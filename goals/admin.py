from django.contrib import admin
from .models import FinancialGoal, GoalContribution


class GoalContributionInline(admin.TabularInline):
    model = GoalContribution
    extra = 0
    readonly_fields = ['created_at']


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_amount', 'current_amount', 'percentage_completed', 'target_date', 'is_completed', 'user']
    list_filter = ['is_completed', 'target_date']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [GoalContributionInline]


@admin.register(GoalContribution)
class GoalContributionAdmin(admin.ModelAdmin):
    list_display = ['goal', 'amount', 'date', 'created_at']
    list_filter = ['date']
    search_fields = ['goal__name', 'notes']
