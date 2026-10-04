from unittest.mock import patch

from django.test import SimpleTestCase

import personal_finance.settings as settings_module


class SupabaseDatabaseConfigTests(SimpleTestCase):
    def test_supabase_s3_endpoint_uses_direct_storage_hostname(self):
        endpoint = settings_module.build_supabase_s3_endpoint(
            'https://project-ref.supabase.co'
        )

        self.assertEqual(
            endpoint,
            'https://project-ref.storage.supabase.co/storage/v1/s3',
        )

    def test_local_file_storage_remains_the_default_outside_vercel(self):
        with patch.object(settings_module, 'USE_SUPABASE_STORAGE', False):
            storage = settings_module.build_default_storage_config()

        self.assertEqual(
            storage['BACKEND'],
            'django.core.files.storage.FileSystemStorage',
        )

    def test_vercel_without_storage_credentials_does_not_use_local_disk(self):
        with patch.multiple(
            settings_module,
            IS_VERCEL=True,
            USE_SUPABASE_STORAGE=True,
            SUPABASE_STORAGE_CONFIGURED=False,
            create=True,
        ):
            storage = settings_module.build_default_storage_config()

        self.assertEqual(
            storage['BACKEND'],
            'core.storage.UnconfiguredStorage',
        )

    def test_supabase_storage_uses_private_signed_s3_urls(self):
        with patch.multiple(
            settings_module,
            create=True,
            USE_SUPABASE_STORAGE=True,
            SUPABASE_STORAGE_CONFIGURED=True,
            SUPABASE_S3_ACCESS_KEY_ID='access-key',
            SUPABASE_S3_SECRET_ACCESS_KEY='secret-key',
            SUPABASE_STORAGE_BUCKET='private-uploads',
            SUPABASE_S3_ENDPOINT=(
                'https://project.supabase.co/storage/v1/s3'
            ),
            SUPABASE_S3_REGION='us-east-1',
        ):
            storage = settings_module.build_default_storage_config()

        self.assertEqual(storage['BACKEND'], 'storages.backends.s3.S3Storage')
        self.assertEqual(storage['OPTIONS']['bucket_name'], 'private-uploads')
        self.assertTrue(storage['OPTIONS']['querystring_auth'])
        self.assertIsNone(storage['OPTIONS']['default_acl'])
        self.assertFalse(storage['OPTIONS']['file_overwrite'])

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

    def test_vercel_uses_postgres_url_even_when_sqlite_is_default(self):
        config_values = {
            'VERCEL': True,
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
        self.assertEqual(database_config['HOST'], 'db.example.supabase.co')

    def test_vercel_without_database_url_never_falls_back_to_sqlite(self):
        with patch.object(
            settings_module,
            'config',
            side_effect=lambda key, default=None, **kwargs: {
                'VERCEL': True,
            }.get(key, default),
        ):
            database_config = settings_module.build_database_config()

        self.assertEqual(
            database_config['ENGINE'],
            'django.db.backends.postgresql',
        )

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
