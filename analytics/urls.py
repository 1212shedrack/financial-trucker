from django.urls import path
from . import views

urlpatterns = [
    path('', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('net-worth/', views.NetWorthView.as_view(), name='net_worth'),
    path('health-score/', views.HealthScoreView.as_view(), name='health_score'),
    path('calendar/', views.CalendarView.as_view(), name='financial_calendar'),
    path('api/summary/', views.AnalyticsSummaryAPIView.as_view(), name='analytics_summary_api'),
    path('api/trends/', views.MonthlyTrendsAPIView.as_view(), name='analytics_trends_api'),
    path('api/categories/', views.CategoryBreakdownAPIView.as_view(), name='analytics_categories_api'),
    path('api/insights/', views.InsightsAPIView.as_view(), name='analytics_insights_api'),
]

