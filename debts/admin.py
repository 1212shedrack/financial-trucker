from django.contrib import admin
from .models import Debt, DebtRepayment


class DebtRepaymentInline(admin.TabularInline):
    model = DebtRepayment
    extra = 0


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'debt_type',
                    'principal_amount', 'status',
                    'due_date']
    list_filter = ['debt_type', 'status']
    search_fields = ['name', 'user__username']
    inlines = [DebtRepaymentInline]
