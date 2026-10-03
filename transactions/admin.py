from django.contrib import admin
from .models import Category, Income, Expense, RecurringTransaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'user', 'is_default', 'created_at']
    list_filter = ['category_type', 'is_default']
    search_fields = ['name']


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['source', 'amount', 'category', 'date', 'payment_method', 'user']
    list_filter = ['category', 'payment_method', 'date']
    search_fields = ['source', 'description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'date', 'payment_method', 'user']
    list_filter = ['category', 'payment_method', 'date']
    search_fields = ['description', 'notes']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'transaction_type', 'frequency', 'next_due_date', 'active', 'user']
    list_filter = ['transaction_type', 'frequency', 'active']
    search_fields = ['title']
