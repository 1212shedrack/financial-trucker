from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from core.views import log_action
from .models import FinancialGoal, GoalContribution
from .forms import FinancialGoalForm, GoalContributionForm
from notifications.services import check_goal_milestones


class GoalListView(LoginRequiredMixin, View):
    template_name = 'goals/goal_list.html'

    def get(self, request):
        active = FinancialGoal.objects.filter(user=request.user, is_completed=False).order_by('-created_at')
        completed = FinancialGoal.objects.filter(user=request.user, is_completed=True).order_by('-updated_at')
        return render(request, self.template_name, {'goals': active, 'completed_goals': completed})


class GoalCreateView(LoginRequiredMixin, View):
    template_name = 'goals/goal_form.html'

    def get(self, request):
        form = FinancialGoalForm(user=request.user)
        return render(request, self.template_name, {'form': form, 'action': 'Create'})

    def post(self, request):
        form = FinancialGoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            log_action(request.user, 'CREATE', f'Created goal: {goal.name}', request)
            messages.success(request, f'Goal "{goal.name}" created!')
            return redirect('goal_list')
        return render(request, self.template_name, {'form': form, 'action': 'Create'})


class GoalUpdateView(LoginRequiredMixin, View):
    template_name = 'goals/goal_form.html'

    def get(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        form = FinancialGoalForm(instance=goal, user=request.user)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': goal})

    def post(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        form = FinancialGoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            log_action(request.user, 'UPDATE', f'Updated goal: {goal.name}', request)
            messages.success(request, 'Goal updated.')
            return redirect('goal_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': goal})


class GoalDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        name = goal.name
        log_action(request.user, 'DELETE', f'Deleted goal: {name}', request)
        goal.delete()
        messages.success(request, f'Goal "{name}" deleted.')
        return redirect('goal_list')


class GoalDetailView(LoginRequiredMixin, View):
    template_name = 'goals/goal_detail.html'

    def get(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        contributions = goal.contributions.all().order_by('-date')
        contrib_form = GoalContributionForm(initial={'date': timezone.now().date()})
        return render(request, self.template_name, {
            'goal': goal,
            'contributions': contributions,
            'contrib_form': contrib_form,
        })


class GoalContributeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        form = GoalContributionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                contribution = form.save(commit=False)
                contribution.goal = goal
                contribution.save()
                goal.current_amount = (goal.current_amount or Decimal('0')) + contribution.amount
                if goal.current_amount >= goal.target_amount:
                    goal.is_completed = True
                goal.save(update_fields=['current_amount', 'is_completed'])
            check_goal_milestones(request.user)
            messages.success(request, f'TSh {contribution.amount:,.0f} added to "{goal.name}".')
        else:
            messages.error(request, 'Invalid contribution. Please check the amount.')
        return redirect('goal_detail', pk=pk)


class GoalMarkCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
        goal.is_completed = True
        goal.save(update_fields=['is_completed'])
        messages.success(request, f'🎉 Goal "{goal.name}" marked as completed!')
        return redirect('goal_list')
