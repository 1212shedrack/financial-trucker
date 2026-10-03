from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Category, Income, Expense, RecurringTransaction
from budgets.models import Budget
from goals.models import FinancialGoal, GoalContribution
from notifications.models import Notification
from core.serializers import (
    CategorySerializer, IncomeSerializer, ExpenseSerializer,
    RecurringTransactionSerializer, BudgetSerializer,
    FinancialGoalSerializer, GoalContributionSerializer, NotificationSerializer
)


class UserOwnedMixin:
    """Restrict all queryset operations to the authenticated user's data."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class IncomeViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = Income.objects.all().select_related('category')
    serializer_class = IncomeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by('-date', '-created_at')


class ExpenseViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all().select_related('category')
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by('-date', '-created_at')


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        return Category.objects.filter(
            Q(user=self.request.user) | Q(is_default=True)
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        cat = self.get_object()
        if cat.user != request.user:
            return Response({'error': 'Cannot modify default categories.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        cat = self.get_object()
        if cat.user != request.user:
            return Response({'error': 'Cannot modify default categories.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        cat = self.get_object()
        if cat.user != request.user:
            return Response({'error': 'Cannot delete default categories.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class RecurringViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = RecurringTransaction.objects.all().select_related('category')
    serializer_class = RecurringTransactionSerializer


class BudgetViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = Budget.objects.all().select_related('category')
    serializer_class = BudgetSerializer


class GoalViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = FinancialGoal.objects.all()
    serializer_class = FinancialGoalSerializer

    @action(detail=True, methods=['post'])
    def contribute(self, request, pk=None):
        from decimal import Decimal
        from django.db import transaction as db_tx
        goal = self.get_object()
        amount_str = request.data.get('amount', '0')
        try:
            amount = Decimal(str(amount_str))
            if amount <= 0:
                raise ValueError
        except Exception:
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
        with db_tx.atomic():
            GoalContribution.objects.create(goal=goal, amount=amount,
                                             date=request.data.get('date', str(__import__('datetime').date.today())))
            goal.current_amount += amount
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
            goal.save(update_fields=['current_amount', 'is_completed'])
        return Response(FinancialGoalSerializer(goal).data)


class GoalContributionViewSet(viewsets.ModelViewSet):
    serializer_class = GoalContributionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GoalContribution.objects.filter(goal__user=self.request.user)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        from django.db import transaction as db_tx
        goal = serializer.validated_data['goal']
        if goal.user != self.request.user:
            raise PermissionDenied("Cannot add contribution to another user's goal.")
        with db_tx.atomic():
            contribution = serializer.save()
            goal.current_amount += contribution.amount
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
            goal.save(update_fields=['current_amount', 'is_completed'])


class SyncView(APIView):
    """
    Accepts a list of offline operations from the PWA client and processes them.
    Each operation: {type, action, data, client_id}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        operations = request.data.get('operations', [])
        if not isinstance(operations, list):
            return Response({'error': 'operations must be a list'}, status=400)

        synced = 0
        failed = 0
        results = []

        for op in operations:
            try:
                result = self._process_operation(op, request.user)
                results.append({'client_id': op.get('client_id'), 'status': 'ok', 'id': result})
                synced += 1
            except Exception as e:
                results.append({'client_id': op.get('client_id'), 'status': 'error', 'error': str(e)})
                failed += 1

        return Response({'synced': synced, 'failed': failed, 'results': results})

    def _process_operation(self, op, user):
        from decimal import Decimal
        from datetime import date as date_cls
        op_type = op.get('type')
        op_action = op.get('action')
        data = op.get('data', {})

        if op_type == 'income':
            if op_action == 'create':
                inc = Income.objects.create(
                    user=user,
                    amount=Decimal(str(data.get('amount', 0))),
                    source=data.get('source', 'Offline entry'),
                    date=date_cls.fromisoformat(data.get('date', str(date_cls.today()))),
                    payment_method=data.get('payment_method', 'cash'),
                    description=data.get('description', ''),
                )
                return inc.id
        elif op_type == 'expense':
            if op_action == 'create':
                exp = Expense.objects.create(
                    user=user,
                    amount=Decimal(str(data.get('amount', 0))),
                    description=data.get('description', 'Offline entry'),
                    date=date_cls.fromisoformat(data.get('date', str(date_cls.today()))),
                    payment_method=data.get('payment_method', 'cash'),
                    notes=data.get('notes', ''),
                )
                return exp.id
        raise ValueError(f'Unknown operation: {op_type}/{op_action}')
