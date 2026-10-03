from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'period', 'start_date', 'user']
    list_filter = ['period', 'start_date']
    search_fields = ['category__name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
