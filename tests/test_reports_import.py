import io
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from transactions.models import Category, Income, Expense
from reports.services import ReportService


class ReportsAndImportTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='Password123!'
        )
        self.cat = Category.objects.create(user=self.user, name='Utilities', category_type='expense')
        Income.objects.create(
            user=self.user, amount=Decimal('1000000'), source='Salary Work', date=date.today(), payment_method='bank'
        )
        Expense.objects.create(
            user=self.user, amount=Decimal('350000'), description='Power bill', category=self.cat, date=date.today(), payment_method='mpesa'
        )

    def test_csv_report_generation(self):
        service = ReportService(self.user)
        csv_bytes = service.generate_csv()
        content = csv_bytes.decode('utf-8-sig')
        self.assertIn('Salary Work', content)
        self.assertIn('Power bill', content)
        self.assertIn('1000000', content)

    def test_excel_report_generation(self):
        service = ReportService(self.user)
        excel_bytes = service.generate_excel()
        self.assertTrue(len(excel_bytes) > 0)
        # Excel zip header
        self.assertTrue(excel_bytes.startswith(b'PK'))

    def test_pdf_report_generation(self):
        service = ReportService(self.user)
        pdf_bytes = service.generate_pdf()
        self.assertTrue(len(pdf_bytes) > 0)
        # PDF header
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_csv_import_validation_valid(self):
        csv_data = (
            "date,type,description,amount,category,payment_method,notes\n"
            "2026-08-01,income,Freelance Project,500000,Salary,mpesa,Project A\n"
            "2026-08-02,expense,Office Supplies,75000,Utilities,cash,Pens\n"
        ).encode('utf-8')

        service = ReportService(self.user)
        res = service.validate_import_csv(io.BytesIO(csv_data))
        self.assertEqual(len(res['valid_rows']), 2)
        self.assertEqual(len(res['errors']), 0)

        # Import them
        imported_res = service.import_transactions(res['valid_rows'])
        self.assertEqual(imported_res['imported'], 2)
        self.assertEqual(Income.objects.filter(user=self.user, source='Freelance Project').count(), 1)
        self.assertEqual(Expense.objects.filter(user=self.user, description='Office Supplies').count(), 1)

    def test_csv_import_validation_invalid_rows(self):
        bad_csv = (
            "date,type,description,amount\n"
            "invalid-date,income,Freelance Project,500000\n"
            "2026-08-02,unknown_type,Office Supplies,-500\n"
        ).encode('utf-8')

        service = ReportService(self.user)
        res = service.validate_import_csv(io.BytesIO(bad_csv))
        self.assertEqual(len(res['valid_rows']), 0)
        self.assertTrue(len(res['errors']) > 0)

    def test_csv_import_duplicate_detection(self):
        """Rows matching existing records by (date, amount, description) must be flagged
        as duplicates and skipped during import — not inserted again."""
        # The setUp already created:
        #   Income: source='Salary Work', amount=1000000, date=today
        #   Expense: description='Power bill', amount=350000, date=today
        today_str = date.today().isoformat()

        duplicate_csv = (
            f"date,type,description,amount,payment_method\n"
            f"{today_str},income,Salary Work,1000000,bank\n"        # exact duplicate of setUp income
            f"{today_str},expense,Power bill,350000,mpesa\n"        # exact duplicate of setUp expense
            f"2026-01-15,income,New Bonus,200000,cash\n"            # brand new — should import
        ).encode('utf-8')

        service = ReportService(self.user)
        res = service.validate_import_csv(io.BytesIO(duplicate_csv))

        # All 3 rows should parse as valid
        self.assertEqual(len(res['valid_rows']), 3)
        self.assertEqual(len(res['errors']), 0)

        # Exactly 2 rows should be flagged as duplicates
        flagged = [r for r in res['valid_rows'] if r.get('is_duplicate')]
        clean   = [r for r in res['valid_rows'] if not r.get('is_duplicate')]
        self.assertEqual(len(flagged), 2, "Expected 2 duplicate rows to be flagged")
        self.assertEqual(len(clean),   1, "Expected 1 new row to be clean")

        # Import — duplicates must be skipped
        import_res = service.import_transactions(res['valid_rows'])
        self.assertEqual(import_res['imported'],   1, "Only 1 new transaction should be imported")
        self.assertEqual(import_res['duplicates'], 2, "2 duplicates should be skipped")
        self.assertEqual(import_res['skipped'],    0, "No error-skipped rows expected")

        # Verify the new income was created once (not twice)
        self.assertEqual(
            Income.objects.filter(user=self.user, source='New Bonus').count(), 1
        )
        # Verify the duplicate income was NOT added again (still exactly 1 row)
        self.assertEqual(
            Income.objects.filter(user=self.user, source='Salary Work').count(), 1
        )
        # Verify the duplicate expense was NOT added again
        self.assertEqual(
            Expense.objects.filter(user=self.user, description='Power bill').count(), 1
        )

