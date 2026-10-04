from unittest.mock import patch

from django.test import SimpleTestCase

import personal_finance.settings as settings_module


class SupabaseDatabaseConfigTests(SimpleTestCase):
    def test_sqlite_is_default_when_postgres_url_is_configured(self):
        config_values = {
            'DATABASE_URL': (
                'postgresql://postgres:postgres@db.example.supabase.co:5432/'
                'postgres?sslmode=require'
            ),
        }
        with patch.object(
            settings_module,
            'config',
            side_effect=lambda key, default=None, **kwargs: config_values.get(
                key, default
            ),
        ):
            database_config = settings_module.build_database_config()

        self.assertEqual(
            database_config['ENGINE'],
            'django.db.backends.sqlite3',
        )
        self.assertTrue(database_config['NAME'].endswith('db.sqlite3'))

    def test_build_database_config_supports_postgres_url(self):
        config_values = {
            'DB_ENGINE': 'django.db.backends.postgresql',
            'DB_NAME': 'postgres',
            'DB_USER': 'postgres',
            'DB_PASSWORD': 'postgres',
            'DB_HOST': 'db.example.supabase.co',
            'DB_PORT': '5432',
            'DATABASE_URL': (
                'postgresql://postgres:postgres@db.example.supabase.co:5432/'
                'postgres?sslmode=require'
            ),
        }
        with patch.object(
            settings_module,
            'config',
            side_effect=lambda key, default=None, **kwargs: config_values.get(
                key, default
            ),
        ):
            database_config = settings_module.build_database_config()

        self.assertEqual(
            database_config['ENGINE'],
            'django.db.backends.postgresql',
        )
        self.assertEqual(database_config['NAME'], 'postgres')
        self.assertEqual(database_config['HOST'], 'db.example.supabase.co')
        self.assertEqual(database_config['PORT'], '5432')
        self.assertEqual(database_config['OPTIONS']['sslmode'], 'require')
