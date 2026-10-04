from decimal import Decimal
from datetime import date
from django.test import TestCase
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
