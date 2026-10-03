from rest_framework import serializers
from transactions.models import Category, Income, Expense, RecurringTransaction
from budgets.models import Budget
from goals.models import FinancialGoal, GoalContribution
from notifications.models import Notification


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'category_type', 'icon', 'color', 'is_default']
        read_only_fields = ['id', 'is_default']


class IncomeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Income
        fields = ['id', 'amount', 'source', 'category', 'category_name', 'date',
                  'payment_method', 'payment_method_display', 'description', 'notes',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'amount', 'description', 'category', 'category_name', 'date',
                  'time', 'payment_method', 'payment_method_display', 'notes',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class RecurringTransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default='')

    class Meta:
        model = RecurringTransaction
        fields = ['id', 'title', 'amount', 'transaction_type', 'category', 'category_name',
                  'payment_method', 'frequency', 'start_date', 'next_due_date',
                  'end_date', 'active', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    spent_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    percentage_used = serializers.IntegerField(read_only=True)
    is_warning = serializers.BooleanField(read_only=True)
    is_exceeded = serializers.BooleanField(read_only=True)

    class Meta:
        model = Budget
        fields = ['id', 'category', 'category_name', 'amount', 'period',
                  'start_date', 'end_date', 'notes', 'spent_amount',
                  'remaining_amount', 'percentage_used', 'is_warning', 'is_exceeded',
                  'created_at']
        read_only_fields = ['id', 'created_at']


class GoalContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalContribution
        fields = ['id', 'goal', 'amount', 'date', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Contribution must be greater than zero.')
        return value


class FinancialGoalSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    percentage_completed = serializers.IntegerField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = FinancialGoal
        fields = ['id', 'name', 'description', 'target_amount', 'current_amount',
                  'target_date', 'category', 'is_completed', 'remaining_amount',
                  'percentage_completed', 'days_remaining', 'created_at', 'updated_at']
        read_only_fields = ['id', 'current_amount', 'is_completed', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
