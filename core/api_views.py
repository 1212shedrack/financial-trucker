import hashlib
import json
import logging

from django.db import IntegrityError, transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Category, Income, Expense, RecurringTransaction
from budgets.models import Budget
from goals.models import FinancialGoal, GoalContribution
from notifications.models import Notification
from core.models import OfflineSyncReceipt
from transactions.services import validate_upload_file
from core.serializers import (
    CategorySerializer, IncomeSerializer, ExpenseSerializer,
    RecurringTransactionSerializer, BudgetSerializer,
    FinancialGoalSerializer, GoalContributionSerializer, NotificationSerializer
)

logger = logging.getLogger(__name__)


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
        if isinstance(operations, str):
            try:
                operations = json.loads(operations)
            except json.JSONDecodeError:
                return Response(
                    {'error': 'operations must contain valid JSON.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if not isinstance(operations, list):
            return Response({'error': 'operations must be a list'}, status=400)
        if len(operations) > 100:
            return Response(
                {'error': 'A maximum of 100 operations can be synced at once.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        synced = 0
        failed = 0
        results = []

        for op in operations:
            client_id = op.get('client_id') if isinstance(op, dict) else None
            try:
                result = self._process_operation(
                    op,
                    request.user,
                    request.FILES,
                )
                results.append({
                    'client_id': client_id,
                    'status': 'ok',
                    'id': result,
                })
                synced += 1
            except SyncValidationError as error:
                results.append({
                    'client_id': client_id,
                    'status': 'error',
                    'error': 'Invalid transaction data.',
                    'details': error.details,
                })
                failed += 1
            except ValueError as error:
                results.append({
                    'client_id': client_id,
                    'status': 'error',
                    'error': str(error),
                })
                failed += 1
            except Exception:
                logger.exception('Unexpected offline sync failure')
                results.append({
                    'client_id': client_id,
                    'status': 'error',
                    'error': 'The operation could not be synchronized.',
                })
                failed += 1

        return Response({'synced': synced, 'failed': failed, 'results': results})

    def _process_operation(self, op, user, files=None):
        files = files or {}
        if not isinstance(op, dict):
            raise ValueError('Each operation must be an object.')
        client_id = op.get('client_id')
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError('Each operation requires a client_id.')
        if len(client_id) > 120:
            raise ValueError('client_id must be 120 characters or fewer.')

        file_key = op.get('file_key')
        upload = files.get(file_key) if isinstance(file_key, str) else None
        if file_key and upload is None:
            raise ValueError('The queued upload is missing its file data.')
        digest = hashlib.sha256()
        digest.update(
            json.dumps(op, sort_keys=True, separators=(',', ':')).encode()
        )
        if upload:
            for chunk in upload.chunks():
                digest.update(chunk)
            upload.seek(0)
        payload_hash = digest.hexdigest()

        try:
            with transaction.atomic():
                receipt = OfflineSyncReceipt.objects.filter(
                    user=user,
                    client_id=client_id,
                ).first()
                if receipt:
                    if receipt.payload_hash != payload_hash:
                        raise ValueError(
                            'client_id was already used for different data.'
                        )
                    return receipt.record_id

                record_id = self._create_operation(op, user, upload)
                OfflineSyncReceipt.objects.create(
                    user=user,
                    client_id=client_id,
                    payload_hash=payload_hash,
                    record_id=record_id,
                )
                return record_id
        except IntegrityError:
            receipt = OfflineSyncReceipt.objects.filter(
                user=user,
                client_id=client_id,
            ).first()
            if receipt and receipt.payload_hash == payload_hash:
                return receipt.record_id
            if receipt:
                raise ValueError(
                    'client_id was already used for different data.'
                )
            raise

    def _create_operation(self, op, user, upload=None):
        from transactions.forms import ExpenseForm, IncomeForm

        op_type = op.get('type')
        op_action = op.get('action')
        data = op.get('data', {})
        if not isinstance(data, dict):
            raise ValueError('Operation data must be an object.')

        expected_file_field = {
            'income': 'attachment',
            'expense': 'receipt',
            'profile': 'profile_photo',
        }.get(op_type)
        file_field = op.get('file_field')
        if upload and file_field != expected_file_field:
            raise ValueError('The uploaded file field is invalid.')
        form_files = {}
        if upload:
            validate_upload_file(upload)
            form_files[file_field] = upload

        if op_type == 'profile' and op_action == 'update':
            from accounts.forms import UserProfileForm
            form = UserProfileForm(
                data,
                files=form_files,
                instance=user.profile,
            )
            if not form.is_valid():
                raise SyncValidationError(form.errors.get_json_data())
            return form.save().pk

        form_class = {
            'income': IncomeForm,
            'expense': ExpenseForm,
        }.get(op_type)
        if form_class and op_action == 'create':
            form = form_class(data, files=form_files, user=user)
            if not form.is_valid():
                raise SyncValidationError(form.errors.get_json_data())
            record = form.save(commit=False)
            record.user = user
            record.save()
            return record.id
        raise ValueError(f'Unknown operation: {op_type}/{op_action}')


class SyncValidationError(Exception):
    def __init__(self, details):
        self.details = details
