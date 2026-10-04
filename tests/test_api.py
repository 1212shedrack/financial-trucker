from decimal import Decimal
import json
from io import BytesIO
from datetime import date
from tempfile import TemporaryDirectory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from transactions.models import Category, Income, Expense


class APITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_api_income_list_and_create(self):
        # Create
        res = self.client.post('/api/income/', {
            'amount': '750000.00',
            'source': 'Consultancy',
            'date': date.today().isoformat(),
            'payment_method': 'bank'
        })
        self.assertEqual(res.status_code, 201)

        # List
        res = self.client.get('/api/income/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 1)

    def test_api_expense_list_and_create(self):
        # Create
        res = self.client.post('/api/expenses/', {
            'amount': '120000.00',
            'description': 'Weekly fuel',
            'date': date.today().isoformat(),
            'payment_method': 'mpesa'
        })
        self.assertEqual(res.status_code, 201)

        # List
        res = self.client.get('/api/expenses/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 1)

    def test_offline_sync_api(self):
        sync_payload = {
            'operations': [
                {
                    'client_id': 'offline_123',
                    'type': 'expense',
                    'action': 'create',
                    'data': {
                        'amount': '25000.00',
                        'description': 'Offline grocery',
                        'date': date.today().isoformat(),
                        'payment_method': 'cash'
                    }
                },
                {
                    'client_id': 'offline_124',
                    'type': 'income',
                    'action': 'create',
                    'data': {
                        'amount': '150000.00',
                        'source': 'Offline freelance',
                        'date': date.today().isoformat(),
                        'payment_method': 'mpesa'
                    }
                }
            ]
        }
        res = self.client.post('/api/sync/', sync_payload, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['synced'], 2)
        self.assertEqual(Expense.objects.filter(user=self.user, description='Offline grocery').count(), 1)
        self.assertEqual(Income.objects.filter(user=self.user, source='Offline freelance').count(), 1)

    def test_offline_sync_retry_does_not_duplicate_record(self):
        operation = {
            'client_id': 'retry_expense_1',
            'type': 'expense',
            'action': 'create',
            'data': {
                'amount': '12000.00',
                'description': 'Queued once',
                'date': date.today().isoformat(),
                'payment_method': 'cash',
            },
        }
        payload = {'operations': [operation]}

        first_response = self.client.post(
            '/api/sync/', payload, format='json'
        )
        retry_response = self.client.post(
            '/api/sync/', payload, format='json'
        )

        self.assertEqual(first_response.data['synced'], 1)
        self.assertEqual(retry_response.data['synced'], 1)
        self.assertEqual(
            first_response.data['results'][0]['id'],
            retry_response.data['results'][0]['id'],
        )
        self.assertEqual(
            Expense.objects.filter(
                user=self.user,
                description='Queued once',
            ).count(),
            1,
        )

    def test_offline_sync_rejects_invalid_amount_without_storing_record(self):
        response = self.client.post(
            '/api/sync/',
            {'operations': [{
                'client_id': 'invalid_expense_1',
                'type': 'expense',
                'action': 'create',
                'data': {
                    'amount': '-1',
                    'description': 'Invalid amount',
                    'date': date.today().isoformat(),
                    'payment_method': 'cash',
                },
            }]},
            format='json',
        )

        self.assertEqual(response.data['failed'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'error')
        self.assertEqual(
            Expense.objects.filter(user=self.user).count(),
            0,
        )

    def test_offline_sync_rejects_another_users_category(self):
        other_user = User.objects.create_user(
            username='otherapiuser',
            email='other-api@example.com',
            password='apipassword123',
        )
        category = Category.objects.create(
            user=other_user,
            name='Private category',
            category_type='income',
        )

        response = self.client.post(
            '/api/sync/',
            {'operations': [{
                'client_id': 'foreign_category_1',
                'type': 'income',
                'action': 'create',
                'data': {
                    'amount': '5000',
                    'source': 'Offline entry',
                    'date': date.today().isoformat(),
                    'payment_method': 'cash',
                    'category': str(category.pk),
                },
            }]},
            format='json',
        )

        self.assertEqual(response.data['failed'], 1)
        self.assertEqual(
            Income.objects.filter(user=self.user).count(),
            0,
        )

    def test_offline_sync_uploads_receipt_and_retry_is_idempotent(self):
        operation = {
            'client_id': 'receipt_retry_1',
            'type': 'expense',
            'action': 'create',
            'file_key': 'upload_receipt_retry_1',
            'file_field': 'receipt',
            'data': {
                'amount': '12000',
                'description': 'Receipt upload',
                'date': date.today().isoformat(),
                'payment_method': 'cash',
            },
        }
        file_content = b'%PDF-1.4\nminimal test receipt\n'

        def sync_once():
            return self.client.post(
                '/api/sync/',
                {
                    'operations': json.dumps([operation]),
                    'upload_receipt_retry_1': SimpleUploadedFile(
                        'receipt.pdf',
                        file_content,
                        content_type='application/pdf',
                    ),
                },
                format='multipart',
            )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                first_response = sync_once()
                retry_response = sync_once()
                expense = Expense.objects.get(
                    user=self.user,
                    description='Receipt upload',
                )

                self.assertEqual(first_response.data['synced'], 1)
                self.assertEqual(retry_response.data['synced'], 1)
                self.assertTrue(expense.receipt.name)
                self.assertTrue(
                    expense.receipt.storage.exists(expense.receipt.name)
                )
                self.assertEqual(
                    Expense.objects.filter(
                user=self.user,
                description='Receipt upload',
                    ).count(),
                    1,
                )

    def test_offline_sync_keeps_record_unsynced_when_file_part_is_missing(self):
        response = self.client.post(
            '/api/sync/',
            {'operations': [{
                'client_id': 'missing_receipt_1',
                'type': 'expense',
                'action': 'create',
                'file_key': 'missing_file_part',
                'file_field': 'receipt',
                'data': {
                    'amount': '12000',
                    'description': 'Missing receipt',
                    'date': date.today().isoformat(),
                    'payment_method': 'cash',
                },
            }]},
            format='json',
        )

        self.assertEqual(response.data['failed'], 1)
        self.assertEqual(
            Expense.objects.filter(
                user=self.user,
                description='Missing receipt',
            ).count(),
            0,
        )

    def test_offline_sync_updates_profile_photo(self):
        from PIL import Image

        image_bytes = BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(image_bytes, format='PNG')
        operation = {
            'client_id': 'profile_photo_1',
            'type': 'profile',
            'action': 'update',
            'file_key': 'upload_profile_photo_1',
            'file_field': 'profile_photo',
            'data': {
                'full_name': 'API User',
                'phone_number': '',
                'preferred_currency': 'TZS',
                'timezone': 'Africa/Dar_es_Salaam',
                'monthly_income_target': '0',
                'monthly_savings_target': '0',
            },
        }

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    '/api/sync/',
                    {
                        'operations': json.dumps([operation]),
                        'upload_profile_photo_1': SimpleUploadedFile(
                            'profile.png',
                            image_bytes.getvalue(),
                            content_type='image/png',
                        ),
                    },
                    format='multipart',
                )
                self.user.profile.refresh_from_db()
                photo = self.user.profile.profile_photo
                self.assertEqual(response.data['synced'], 1)
                self.assertTrue(photo.storage.exists(photo.name))
