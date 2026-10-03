from unittest.mock import patch

from django.test import SimpleTestCase

import personal_finance.settings as settings_module


class SupabaseDatabaseConfigTests(SimpleTestCase):
    def test_build_database_config_supports_postgres_url(self):
        with patch.object(settings_module, 'config', side_effect=lambda key, default=None, **kwargs: {
            'DB_ENGINE': 'django.db.backends.postgresql',
            'DB_NAME': 'postgres',
            'DB_USER': 'postgres',
            'DB_PASSWORD': 'postgres',
            'DB_HOST': 'db.example.supabase.co',
            'DB_PORT': '5432',
            'DATABASE_URL': 'postgresql://postgres:postgres@db.example.supabase.co:5432/postgres?sslmode=require',
        }.get(key, default)):
            config = settings_module.build_database_config()

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'postgres')
        self.assertEqual(config['HOST'], 'db.example.supabase.co')
        self.assertEqual(config['PORT'], '5432')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')
