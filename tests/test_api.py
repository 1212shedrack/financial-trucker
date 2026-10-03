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
