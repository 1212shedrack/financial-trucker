from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage


class UnconfiguredStorage(Storage):
    def _open(self, name, mode='rb'):
        raise ImproperlyConfigured(
            'Configure Supabase Storage credentials before accessing uploads.'
        )

    def _save(self, name, content):
        raise ImproperlyConfigured(
            'Configure Supabase Storage credentials before saving uploads.'
        )

    def exists(self, name):
        return False

    def url(self, name):
        return ''

    def delete(self, name):
        return None