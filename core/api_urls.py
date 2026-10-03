from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.api_views import (
    IncomeViewSet, ExpenseViewSet, CategoryViewSet, RecurringViewSet,
    BudgetViewSet, GoalViewSet, GoalContributionViewSet, SyncView
)
from analytics.views import (
    AnalyticsSummaryAPIView, MonthlyTrendsAPIView,
    CategoryBreakdownAPIView, InsightsAPIView
)
from notifications.views import NotificationAPIView

router = DefaultRouter()
router.register(r'income', IncomeViewSet, basename='api-income')
router.register(r'expenses', ExpenseViewSet, basename='api-expense')
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'budgets', BudgetViewSet, basename='api-budget')
router.register(r'goals', GoalViewSet, basename='api-goal')
router.register(r'goal-contributions', GoalContributionViewSet, basename='api-goal-contribution')
router.register(r'recurring', RecurringViewSet, basename='api-recurring')

urlpatterns = router.urls + [
    path('analytics/summary/', AnalyticsSummaryAPIView.as_view(), name='api-analytics-summary'),
    path('analytics/trends/', MonthlyTrendsAPIView.as_view(), name='api-analytics-trends'),
    path('analytics/categories/', CategoryBreakdownAPIView.as_view(), name='api-analytics-categories'),
    path('analytics/insights/', InsightsAPIView.as_view(), name='api-insights'),
    path('notifications/', NotificationAPIView.as_view(), name='api-notifications'),
    path('sync/', SyncView.as_view(), name='api-sync'),
]
