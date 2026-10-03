import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from analytics.services import FinancialAnalyticsService
from core.views import _get_date_range


class AnalyticsDashboardView(LoginRequiredMixin, View):
    template_name = 'analytics/dashboard.html'

    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        range_param = request.GET.get('range', 'month')
        date_from, date_to = _get_date_range(range_param, request)

        summary = service.get_summary(date_from, date_to)
        monthly_trends = service.get_monthly_trends(12)
        category_breakdown = service.get_expense_by_category(date_from, date_to)
        payment_dist = service.get_payment_method_distribution(date_from, date_to)
        daily_spending = service.get_daily_spending(date_from, date_to)
        income_sources = service.get_income_sources(date_from, date_to)
        budget_perf = service.get_budget_performance()
        anomalies = service.detect_anomalies()

        context = {
            'summary': summary,
            'monthly_trends_json': json.dumps(monthly_trends),
            'category_breakdown_json': json.dumps(category_breakdown),
            'payment_dist_json': json.dumps(payment_dist),
            'daily_spending_json': json.dumps(daily_spending),
            'income_sources_json': json.dumps(income_sources),
            'budget_perf_json': json.dumps(budget_perf),
            'anomalies': anomalies,
            'range_param': range_param,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, self.template_name, context)


class AnalyticsSummaryAPIView(LoginRequiredMixin, View):
    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        range_param = request.GET.get('range', 'month')
        date_from, date_to = _get_date_range(range_param, request)
        return JsonResponse(service.get_summary(date_from, date_to))


class MonthlyTrendsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        months = int(request.GET.get('months', 12))
        return JsonResponse(service.get_monthly_trends(months))


class CategoryBreakdownAPIView(LoginRequiredMixin, View):
    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        return JsonResponse({'data': service.get_expense_by_category()})


class InsightsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        return JsonResponse({'insights': service.generate_insights()})


class NetWorthView(LoginRequiredMixin, View):
    template_name = 'analytics/net_worth.html'

    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        net_worth_data = service.get_net_worth()
        return render(request, self.template_name, {
            'data': net_worth_data,
            'net_worth_json': json.dumps(net_worth_data),
        })


class HealthScoreView(LoginRequiredMixin, View):
    template_name = 'analytics/health_score.html'

    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        score_data = service.calculate_health_score()
        forecast_data = service.get_expense_forecast()
        return render(request, self.template_name, {
            'score': score_data,
            'forecast': forecast_data,
        })


class CalendarView(LoginRequiredMixin, View):
    template_name = 'analytics/calendar.html'

    def get(self, request):
        service = FinancialAnalyticsService(request.user)
        events = service.get_financial_calendar(days_ahead=90)
        return render(request, self.template_name, {
            'events': events,
            'events_json': json.dumps(events),
        })
