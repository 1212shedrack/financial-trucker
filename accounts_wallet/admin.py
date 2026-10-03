from django.contrib import admin
from .models import Account, Transfer


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'account_type', 'opening_balance', 'is_active']
    list_filter = ['account_type', 'is_active']
    search_fields = ['name', 'user__username']


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['user', 'from_account', 'to_account', 'amount', 'date']
    list_filter = ['date']
    search_fields = ['user__username', 'from_account__name', 'to_account__name']
