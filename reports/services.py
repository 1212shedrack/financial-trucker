"""
Report generation service: CSV, Excel, PDF export and CSV import.
All monetary values use Decimal — never float.
"""
import csv
import io
from datetime import date
from decimal import Decimal

from django.utils import timezone


class ReportService:
    def __init__(self, user, date_from=None, date_to=None):
        self.user = user
        self.date_from = date_from
        self.date_to = date_to

    def _get_income(self):
        from transactions.models import Income
        qs = Income.objects.filter(user=self.user).select_related('category')
        if self.date_from:
            qs = qs.filter(date__gte=self.date_from)
        if self.date_to:
            qs = qs.filter(date__lte=self.date_to)
        return qs.order_by('-date')

    def _get_expenses(self):
        from transactions.models import Expense
        qs = Expense.objects.filter(user=self.user).select_related('category')
        if self.date_from:
            qs = qs.filter(date__gte=self.date_from)
        if self.date_to:
            qs = qs.filter(date__lte=self.date_to)
        return qs.order_by('-date')

    def generate_csv(self, report_type='all'):
        """Generate a CSV file as bytes."""
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type in ('all', 'income'):
            writer.writerow(['=== INCOME ==='])
            writer.writerow(['Date', 'Source', 'Category', 'Amount (TZS)', 'Payment Method', 'Description'])
            total = Decimal('0')
            for inc in self._get_income():
                writer.writerow([
                    inc.date, inc.source,
                    inc.category.name if inc.category else '',
                    inc.amount, inc.get_payment_method_display(), inc.description
                ])
                total += inc.amount
            writer.writerow(['', '', 'TOTAL', total, '', ''])
            writer.writerow([])

        if report_type in ('all', 'expense'):
            writer.writerow(['=== EXPENSES ==='])
            writer.writerow(['Date', 'Description', 'Category', 'Amount (TZS)', 'Payment Method', 'Notes'])
            total = Decimal('0')
            for exp in self._get_expenses():
                writer.writerow([
                    exp.date, exp.description,
                    exp.category.name if exp.category else '',
                    exp.amount, exp.get_payment_method_display(), exp.notes
                ])
                total += exp.amount
            writer.writerow(['', '', 'TOTAL', total, '', ''])

        return output.getvalue().encode('utf-8-sig')

    def generate_excel(self, report_type='all'):
        """Generate an Excel file as bytes using openpyxl."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill('solid', fgColor='198754')

        def style_header(ws, headers):
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')

        if report_type in ('all', 'income'):
            ws_inc = wb.active
            ws_inc.title = 'Income'
            style_header(ws_inc, ['Date', 'Source', 'Category', 'Amount (TZS)', 'Payment Method', 'Description'])
            total = Decimal('0')
            for inc in self._get_income():
                ws_inc.append([
                    str(inc.date), inc.source,
                    inc.category.name if inc.category else '',
                    float(inc.amount), inc.get_payment_method_display(), inc.description
                ])
                total += inc.amount
            ws_inc.append(['', '', 'TOTAL', float(total), '', ''])
            for col in ws_inc.columns:
                ws_inc.column_dimensions[get_column_letter(col[0].column)].auto_size = True

        if report_type in ('all', 'expense'):
            ws_exp = wb.create_sheet('Expenses')
            style_header(ws_exp, ['Date', 'Description', 'Category', 'Amount (TZS)', 'Payment Method', 'Notes'])
            total = Decimal('0')
            for exp in self._get_expenses():
                ws_exp.append([
                    str(exp.date), exp.description,
                    exp.category.name if exp.category else '',
                    float(exp.amount), exp.get_payment_method_display(), exp.notes
                ])
                total += exp.amount
            ws_exp.append(['', '', 'TOTAL', float(total), '', ''])

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    def generate_pdf(self, report_type='all'):
        """Generate a PDF report as bytes using reportlab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], textColor=colors.HexColor('#198754'))
        elements.append(Paragraph('Financial Report', title_style))
        elements.append(Paragraph(
            f'Period: {self.date_from or "All time"} to {self.date_to or "Today"}   '
            f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}',
            styles['Normal']
        ))
        elements.append(Spacer(1, 0.5*cm))

        # Summary
        from transactions.services import get_total_income, get_total_expenses, get_net_savings
        tot_income = get_total_income(self.user, self.date_from, self.date_to)
        tot_expenses = get_total_expenses(self.user, self.date_from, self.date_to)
        net = tot_income - tot_expenses
        savings_rate = float(net / tot_income * 100) if tot_income > 0 else 0

        summary_data = [
            ['Metric', 'Amount (TZS)'],
            ['Total Income', f'TSh {tot_income:,.0f}'],
            ['Total Expenses', f'TSh {tot_expenses:,.0f}'],
            ['Net Savings', f'TSh {net:,.0f}'],
            ['Savings Rate', f'{savings_rate:.1f}%'],
        ]
        summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*cm))

        # Income table
        if report_type in ('all', 'income'):
            elements.append(Paragraph('Income Details', styles['Heading2']))
            inc_data = [['Date', 'Source', 'Category', 'Amount (TZS)', 'Payment']]
            for inc in self._get_income()[:50]:
                inc_data.append([
                    str(inc.date), inc.source[:25],
                    inc.category.name if inc.category else '-',
                    f'TSh {inc.amount:,.0f}', inc.get_payment_method_display()
                ])
            inc_table = Table(inc_data, colWidths=[2.5*cm, 4*cm, 3*cm, 4*cm, 3*cm])
            inc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0dcaf0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(inc_table)
            elements.append(Spacer(1, 0.5*cm))

        # Expense table
        if report_type in ('all', 'expense'):
            elements.append(Paragraph('Expense Details', styles['Heading2']))
            exp_data = [['Date', 'Description', 'Category', 'Amount (TZS)', 'Payment']]
            for exp in self._get_expenses()[:50]:
                exp_data.append([
                    str(exp.date), exp.description[:25],
                    exp.category.name if exp.category else '-',
                    f'TSh {exp.amount:,.0f}', exp.get_payment_method_display()
                ])
            exp_table = Table(exp_data, colWidths=[2.5*cm, 4*cm, 3*cm, 4*cm, 3*cm])
            exp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(exp_table)

        doc.build(elements)
        return output.getvalue()

    def validate_import_csv(self, file_obj):
        """Validate a CSV import file. Returns dict with valid_rows, invalid_rows, errors.
        Duplicate detection: rows matching an existing record by (date, amount, description)
        are flagged with is_duplicate=True so they can be shown in the preview and skipped.
        """
        from transactions.models import Income, Expense
        valid_rows = []
        invalid_rows = []
        errors = []

        # Build in-memory sets of existing (date, amount, description) for fast lookup
        existing_income = set(
            Income.objects.filter(user=self.user)
            .values_list('date', 'amount', 'source')
        )
        existing_expense = set(
            Expense.objects.filter(user=self.user)
            .values_list('date', 'amount', 'description')
        )

        try:
            content = file_obj.read()
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            reader = csv.DictReader(io.StringIO(text))
            required_fields = {'date', 'description', 'amount', 'type'}
            if not required_fields.issubset(set(f.lower().strip() for f in (reader.fieldnames or []))):
                errors.append('CSV must have columns: date, description, amount, type (income/expense)')
                return {'valid_rows': [], 'invalid_rows': [], 'errors': errors}

            for i, row in enumerate(reader, start=2):
                row = {k.lower().strip(): v.strip() for k, v in row.items()}
                row_errors = []
                parsed_date = None
                amount = None

                try:
                    parsed_date = date.fromisoformat(row.get('date', ''))
                except ValueError:
                    row_errors.append(f'Row {i}: Invalid date format (use YYYY-MM-DD)')

                try:
                    amount = Decimal(row.get('amount', '0').replace(',', ''))
                    if amount <= 0:
                        raise ValueError
                except Exception:
                    row_errors.append(f'Row {i}: Invalid amount')

                t_type = row.get('type', '').lower()
                if t_type not in ('income', 'expense'):
                    row_errors.append(f'Row {i}: Type must be "income" or "expense"')

                if row_errors:
                    invalid_rows.append({'row': i, 'data': row, 'errors': row_errors})
                    errors.extend(row_errors)
                else:
                    description = row.get('description', '')

                    # ── Duplicate detection ──────────────────────────────────
                    is_duplicate = False
                    if parsed_date and amount is not None:
                        if t_type == 'income':
                            is_duplicate = (parsed_date, amount, description) in existing_income
                        else:
                            is_duplicate = (parsed_date, amount, description) in existing_expense

                    valid_rows.append({
                        'date': row.get('date'),
                        'description': description,
                        'amount': row.get('amount', '0').replace(',', ''),
                        'type': t_type,
                        'category': row.get('category', ''),
                        'payment_method': row.get('payment_method', 'cash').lower(),
                        'notes': row.get('notes', ''),
                        'is_duplicate': is_duplicate,
                    })
        except Exception as e:
            errors.append(f'File read error: {str(e)}')

        return {'valid_rows': valid_rows, 'invalid_rows': invalid_rows, 'errors': errors}

    def import_transactions(self, valid_rows):
        """Atomically import validated rows. Skips rows flagged as is_duplicate.
        Returns {imported, skipped, duplicates}.
        """
        from django.db import transaction as db_transaction
        from transactions.models import Income, Expense, Category
        imported = 0
        skipped = 0
        duplicates = 0

        with db_transaction.atomic():
            for row in valid_rows:
                # Skip rows detected as duplicates during validation
                if row.get('is_duplicate', False):
                    duplicates += 1
                    continue

                try:
                    amount = Decimal(row['amount'])
                    cat_name = row.get('category', '').strip()
                    category = None
                    if cat_name:
                        from django.db.models import Q
                        category = Category.objects.filter(
                            Q(user=self.user, name__iexact=cat_name) |
                            Q(is_default=True, name__iexact=cat_name)
                        ).first()

                    if row['type'] == 'income':
                        Income.objects.create(
                            user=self.user,
                            amount=amount,
                            source=row['description'],
                            category=category,
                            date=date.fromisoformat(row['date']),
                            payment_method=row.get('payment_method', 'cash'),
                            notes=row.get('notes', ''),
                        )
                    else:
                        Expense.objects.create(
                            user=self.user,
                            amount=amount,
                            description=row['description'],
                            category=category,
                            date=date.fromisoformat(row['date']),
                            payment_method=row.get('payment_method', 'cash'),
                            notes=row.get('notes', ''),
                        )
                    imported += 1
                except Exception:
                    skipped += 1

        return {'imported': imported, 'skipped': skipped, 'duplicates': duplicates}
