import logging
from decimal import Decimal
from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.db.models import Sum, Count, Avg, Value
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone

logger = logging.getLogger("analytics")


class FinancialAnalyticsService:

    def __init__(self, user):
        self.user = user
        self._income_dfs = {}
        self._expense_dfs = {}

    # Private helpers

    def _get_income_queryset(self, date_from=None, date_to=None):
        from transactions.models import Income

        qs = Income.objects.filter(user=self.user).select_related("category")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def _get_expense_queryset(self, date_from=None, date_to=None):
        from transactions.models import Expense

        qs = Expense.objects.filter(user=self.user).select_related("category")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def _get_income_df(self, date_from=None, date_to=None):
        key = (date_from, date_to)
        if key in self._income_dfs:
            return self._income_dfs[key]

        qs = self._get_income_queryset(date_from=date_from, date_to=date_to)
        if not date_from and not date_to:
            qs = qs.filter(
                date__gte=(timezone.now().date() - timedelta(days=365))
            )

        records = list(
            qs.values(
                "id",
                "amount",
                "source",
                "category__name",
                "date",
                "payment_method",
            )[:50000]
        )
        if not records:
            df = pd.DataFrame(
                columns=[
                    "id",
                    "amount",
                    "source",
                    "category",
                    "date",
                    "payment_method",
                ]
            )
        else:
            df = pd.DataFrame(records)
            df.rename(columns={"category__name": "category"}, inplace=True)
            df["amount"] = df["amount"].astype(float)
            df["date"] = pd.to_datetime(df["date"])

        self._income_dfs[key] = df
        return df

    def _get_expense_df(self, date_from=None, date_to=None):
        key = (date_from, date_to)
        if key in self._expense_dfs:
            return self._expense_dfs[key]

        qs = self._get_expense_queryset(date_from=date_from, date_to=date_to)
        if not date_from and not date_to:
            qs = qs.filter(
                date__gte=(timezone.now().date() - timedelta(days=365))
            )

        records = list(
            qs.values(
                "id",
                "amount",
                "description",
                "category__name",
                "date",
                "payment_method",
            )[:50000]
        )
        if not records:
            df = pd.DataFrame(
                columns=[
                    "id",
                    "amount",
                    "description",
                    "category",
                    "date",
                    "payment_method",
                ]
            )
        else:
            df = pd.DataFrame(records)
            df.rename(columns={"category__name": "category"}, inplace=True)
            df["amount"] = df["amount"].astype(float)
            df["date"] = pd.to_datetime(df["date"])

        self._expense_dfs[key] = df
        return df

    # Summary

    def get_summary(self, date_from=None, date_to=None, transaction_type="all"):
        type_filter = (transaction_type or "all").lower()
        if type_filter not in {"all", "income", "expense"}:
            type_filter = "all"

        income_qs = (
            self._get_income_queryset(date_from=date_from, date_to=date_to)
            if type_filter in {"all", "income"}
            else self._get_income_queryset(date_from=None, date_to=None).none()
        )
        expense_qs = (
            self._get_expense_queryset(date_from=date_from, date_to=date_to)
            if type_filter in {"all", "expense"}
            else self._get_expense_queryset(date_from=None, date_to=None).none()
        )

        income_totals = income_qs.aggregate(
            total_income=Sum("amount"), income_count=Count("id")
        )
        expense_totals = expense_qs.aggregate(
            total_expenses=Sum("amount"), expense_count=Count("id")
        )

        total_income = float(income_totals["total_income"] or 0)
        total_expenses = float(expense_totals["total_expenses"] or 0)
        income_count = int(income_totals["income_count"] or 0)
        expense_count = int(expense_totals["expense_count"] or 0)
        net_savings = total_income - total_expenses
        savings_rate = (
            (net_savings / total_income * 100) if total_income > 0 else 0.0
        )

        if date_from and date_to:
            period_days = max((date_to - date_from).days + 1, 1)
        elif expense_qs.exists():
            min_date = (
                expense_qs.order_by("date")
                .values_list("date", flat=True)
                .first()
            )
            max_date = (
                expense_qs.order_by("-date")
                .values_list("date", flat=True)
                .first()
            )
            period_days = max((max_date - min_date).days + 1, 1)
        else:
            period_days = 1
        avg_daily = total_expenses / max(period_days, 1)

        average_expense = (
            (total_expenses / expense_count) if expense_count else 0.0
        )

        highest_expense = float(
            expense_qs.order_by("-amount")
            .values_list("amount", flat=True)
            .first()
            or 0
        )

        top_category = (
            expense_qs.values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
            .first()
        )
        top_category = top_category["category__name"] if top_category else None

        most_used_method = (
            expense_qs.values("payment_method")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )
        most_used_method = (
            most_used_method["payment_method"] if most_used_method else None
        )

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "savings_rate": round(savings_rate, 1),
            "avg_daily_spending": round(avg_daily, 0),
            "average_expense": round(average_expense, 0),
            "transaction_count": income_count + expense_count,
            "highest_expense": highest_expense,
            "top_category": top_category,
            "most_used_payment_method": most_used_method,
            "income_count": income_count,
            "expense_count": expense_count,
        }

    # Monthly Trends

    def get_monthly_trends(self, months=12, date_from=None, date_to=None, transaction_type="all"):
        today = timezone.now().date()
        if date_from is None:
            month_start = today.replace(day=1)
        else:
            month_start = date_from.replace(day=1) if hasattr(date_from, "replace") else date_from
        if date_to is not None and hasattr(date_to, "replace"):
            anchor_date = date_to
        else:
            anchor_date = today

        type_filter = (transaction_type or "all").lower()
        if type_filter not in {"all", "income", "expense"}:
            type_filter = "all"

        start_month = month_start - pd.DateOffset(months=months - 1)
        start_month = start_month.date() if hasattr(start_month, "date") else start_month

        income_qs = (
            self._get_income_queryset(date_from=start_month, date_to=anchor_date)
            if type_filter in {"all", "income"}
            else self._get_income_queryset(date_from=None, date_to=None).none()
        )
        expense_qs = (
            self._get_expense_queryset(date_from=start_month, date_to=anchor_date)
            if type_filter in {"all", "expense"}
            else self._get_expense_queryset(date_from=None, date_to=None).none()
        )

        income_by_month = {
            self._as_date(month_value): float(total or 0)
            for month_value, total in income_qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .values_list("month", "total")
        }
        expense_by_month = {
            self._as_date(month_value): float(total or 0)
            for month_value, total in expense_qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .values_list("month", "total")
        }

        labels = []
        income_data = []
        expense_data = []
        savings_data = []

        for i in range(months):
            month_date = month_start - pd.DateOffset(months=months - 1 - i)
            month_key = month_date.date() if hasattr(month_date, "date") else month_date
            labels.append(month_date.strftime("%b %Y"))

            month_income = float(income_by_month.get(month_key, 0) or 0)
            month_expense = float(expense_by_month.get(month_key, 0) or 0)

            income_data.append(round(month_income, 0))
            expense_data.append(round(month_expense, 0))
            savings_data.append(round(month_income - month_expense, 0))

        return {
            "labels": labels,
            "income_data": income_data,
            "expense_data": expense_data,
            "savings_data": savings_data,
            "income": income_data,
            "expenses": expense_data,
            "savings": savings_data,
        }

    # Category Breakdown

    def get_expense_by_category(self, date_from=None, date_to=None):
        expense_qs = self._get_expense_queryset(
            date_from=date_from, date_to=date_to
        )
        total = float(expense_qs.aggregate(total=Sum("amount"))["total"] or 0)

        category_groups = (
            expense_qs.values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        result = []
        for item in category_groups:
            category_name = item["category__name"] or "Uncategorized"
            amount = float(item["total"] or 0)
            result.append(
                {
                    "category": category_name,
                    "amount": round(amount, 0),
                    "percentage": (
                        round((amount / total) * 100, 1) if total > 0 else 0
                    ),
                }
            )
        return result

    def get_payment_method_distribution(self, date_from=None, date_to=None):
        expense_qs = self._get_expense_queryset(
            date_from=date_from, date_to=date_to
        )
        total = float(expense_qs.aggregate(total=Sum("amount"))["total"] or 0)
        method_groups = (
            expense_qs.values("payment_method")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        result = []
        labels = {
            "cash": "Cash",
            "mpesa": "M-Pesa",
            "airtel": "Airtel Money",
            "tigo": "Tigo Pesa",
            "halotel": "Halotel",
            "bank": "Bank",
            "card": "Card",
            "other": "Other",
        }
        for item in method_groups:
            method = item["payment_method"]
            amount = float(item["total"] or 0)
            result.append(
                {
                    "method": labels.get(method, method),
                    "amount": round(amount, 0),
                    "percentage": (
                        round((amount / total) * 100, 1) if total > 0 else 0
                    ),
                }
            )
        return result

    def get_daily_spending(self, date_from=None, date_to=None):
        expense_qs = self._get_expense_queryset(
            date_from=date_from, date_to=date_to
        )
        daily = (
            expense_qs.annotate(day=TruncDay("date"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        return [
            {
                "date": str(self._as_date(item["day"])),
                "amount": round(float(item["total"] or 0), 0),
            }
            for item in daily
        ]

    def get_income_sources(self, date_from=None, date_to=None):
        income_qs = self._get_income_queryset(
            date_from=date_from, date_to=date_to
        )
        total = float(income_qs.aggregate(total=Sum("amount"))["total"] or 0)
        src_groups = (
            income_qs.values("source")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        return [
            {
                "source": item["source"],
                "amount": round(float(item["total"] or 0), 0),
                "percentage": (
                    round((float(item["total"] or 0) / total) * 100, 1)
                    if total > 0
                    else 0
                ),
            }
            for item in src_groups
        ]

    # Anomaly Detection

    @staticmethod
    def _as_date(value):
        if value is None:
            return None
        if hasattr(value, "date") and not isinstance(value, date):
            return value.date()
        return value

    def detect_anomalies(self, threshold_z=2.0):
        """
        Detect unusual expenses using Z-score on bounded daily spending data.
        This stays small enough for Pandas while avoiding full-history scans.
        """
        date_from = timezone.now().date() - timedelta(days=180)
        expense_qs = self._get_expense_queryset(date_from=date_from)
        daily = list(
            expense_qs.annotate(day=TruncDay("date"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        if len(daily) < 5:
            return []

        values = [float(item["total"] or 0) for item in daily]
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return []

        anomalies = []
        for item in daily:
            raw_day = item["day"]
            day = self._as_date(raw_day)
            if day is None:
                continue
            amount = float(item["total"] or 0)
            z_score = (amount - mean) / std
            if z_score > threshold_z:
                day_expenses = list(
                    expense_qs.filter(date=day).values(
                        "description", "amount"
                    )[:5]
                )
                anomalies.append(
                    {
                        "date": str(day),
                        "total_amount": round(amount, 0),
                        "z_score": round(float(z_score), 2),
                        "average": round(float(mean), 0),
                        "transactions": [
                            {
                                "description": e["description"],
                                "amount": float(e["amount"]),
                            }
                            for e in day_expenses
                        ],
                    }
                )
        return sorted(anomalies, key=lambda x: x["z_score"], reverse=True)[:10]

    # Financial Insights

    def generate_insights(self):
        """
        Generate rule-based financial insights.
        Architecture is ML-ready: replace rules with model predictions in v2.
        """
        insights = []
        today = timezone.now().date()

        # Current month date range
        curr_start = today.replace(day=1)
        prev_month_last = curr_start - timedelta(days=1)
        prev_start = prev_month_last.replace(day=1)

        curr_expenses = self._get_expense_df(
            date_from=curr_start, date_to=today
        )
        prev_expenses = self._get_expense_df(
            date_from=prev_start, date_to=prev_month_last
        )
        curr_income = self._get_income_df(date_from=curr_start, date_to=today)

        # Rule 1: Category spending increase (>20%)
        if not curr_expenses.empty and not prev_expenses.empty:
            curr_cat = curr_expenses.groupby("category")["amount"].sum()
            prev_cat = prev_expenses.groupby("category")["amount"].sum()
            for cat in curr_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    change = (
                        (curr_cat[cat] - prev_cat[cat]) / prev_cat[cat] * 100
                    )
                    if change > 20:
                        insights.append(
                            {
                                "type": "spending_increase",
                                "title": f"Spending Increase: {cat}",
                                "message": (
                                    f"Your {cat} spending is {change:.0f}% "
                                    "higher than last month."
                                ),
                                "severity": "warning",
                                "icon": "bi-arrow-up-circle",
                            }
                        )
                    elif change < -20:
                        insights.append(
                            {
                                "type": "spending_decrease",
                                "title": f"Great Saving: {cat}",
                                "message": (
                                    f"Your {cat} spending is "
                                    f"{abs(change):.0f}% "
                                    "lower than last month."
                                ),
                                "severity": "success",
                                "icon": "bi-arrow-down-circle",
                            }
                        )

        # Rule 2: Savings rate evaluation
        curr_summary = self.get_summary(date_from=curr_start, date_to=today)
        savings_rate = curr_summary["savings_rate"]
        if savings_rate >= 30:
            insights.append(
                {
                    "type": "savings_excellent",
                    "title": "Excellent Savings Rate!",
                    "message": (
                        f"You are saving {savings_rate:.1f}% of your income "
                        "this month. Keep it up!"
                    ),
                    "severity": "success",
                    "icon": "bi-piggy-bank",
                }
            )
        elif savings_rate < 0:
            insights.append(
                {
                    "type": "overspending",
                    "title": "Overspending Alert",
                    "message": (
                        "You are spending more than you earn this month. "
                        "Review your expenses."
                    ),
                    "severity": "danger",
                    "icon": "bi-exclamation-triangle",
                }
            )
        elif savings_rate < 10 and curr_summary["total_income"] > 0:
            insights.append(
                {
                    "type": "low_savings",
                    "title": "Low Savings Rate",
                    "message": (
                        f"You are only saving {savings_rate:.1f}% of income. "
                        "Target at least 20%."
                    ),
                    "severity": "warning",
                    "icon": "bi-piggy-bank",
                }
            )

        # Rule 3: Top spending category
        if curr_summary["top_category"]:
            insights.append(
                {
                    "type": "top_category",
                    "title": f'Top Spending: {curr_summary["top_category"]}',
                    "message": (
                        "Your highest spending category this month is "
                        f'{curr_summary["top_category"]}.'
                    ),
                    "severity": "info",
                    "icon": "bi-bar-chart",
                }
            )

        # Rule 4: Budget alerts
        from budgets.models import Budget

        budgets = Budget.objects.filter(
            user=self.user, period="monthly"
        ).select_related("category")
        for budget in budgets:
            if budget.is_exceeded:
                insights.append(
                    {
                        "type": "budget_exceeded",
                        "title": f"Budget Exceeded: {budget.category.name}",
                        "message": (
                            f"You have exceeded your {budget.category.name} "
                            "budget by TSh "
                            f"{abs(float(budget.remaining_amount)):,.0f}."
                        ),
                        "severity": "danger",
                        "icon": "bi-x-circle",
                    }
                )
            elif budget.is_warning:
                insights.append(
                    {
                        "type": "budget_warning",
                        "title": f"Budget Alert: {budget.category.name}",
                        "message": (
                            f"You have used {budget.percentage_used}% of your "
                            f"{budget.category.name} budget."
                        ),
                        "severity": "warning",
                        "icon": "bi-exclamation-triangle",
                    }
                )

        # Rule 5: Anomaly detection
        anomalies = self.detect_anomalies()
        if anomalies:
            insights.append(
                {
                    "type": "unusual_spending",
                    "title": "Unusual Spending Detected",
                    "message": (
                        f'Your spending on {anomalies[0]["date"]} was '
                        f'{anomalies[0]["z_score"]}x above your average '
                        "daily spending."
                    ),
                    "severity": "warning",
                    "icon": "bi-graph-up-arrow",
                }
            )

        return insights[:8]  # Return top 8 insights

    # Budget Performance

    def get_budget_performance(self):
        from budgets.models import Budget

        budgets = Budget.objects.filter(
            user=self.user, period="monthly"
        ).select_related("category")
        result = []
        for b in budgets:
            result.append(
                {
                    "category": b.category.name,
                    "budget": float(b.amount),
                    "spent": float(b.spent_amount),
                    "percentage": b.percentage_used,
                    "status": b.status_class,
                }
            )
        return result

    # Net Worth, Health Score, Forecasting & Calendar

    def get_net_worth(self):
        """
        Calculate user's Net Worth:
        Total Assets = balances + goals saved + receivables.
        Total Liabilities = Debts Owed (loans)
        Net Worth = Total Assets - Total Liabilities
        """
        from accounts_wallet.models import Account
        from debts.models import Debt
        from goals.models import FinancialGoal

        # Accounts total balance
        accounts = Account.objects.filter(user=self.user, is_active=True).with_current_balance()
        liquid_assets = sum(acc.current_balance for acc in accounts)

        # Receivables (owed to user)
        receivables = Debt.objects.filter(
            user=self.user, debt_type="receivable"
        )
        total_receivable = sum(d.remaining_balance for d in receivables)

        # Total Assets
        total_assets = liquid_assets + total_receivable

        # Liabilities (loans user owes)
        loans = Debt.objects.filter(user=self.user, debt_type="loan")
        total_liabilities = sum(d.remaining_balance for d in loans)

        net_worth = total_assets - total_liabilities

        return {
            "liquid_assets": float(liquid_assets),
            "receivables": float(total_receivable),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "net_worth": float(net_worth),
            "asset_breakdown": [
                {
                    "name": acc.name,
                    "type": acc.get_account_type_display(),
                    "amount": float(acc.current_balance),
                }
                for acc in accounts
            ],
            "liability_breakdown": [
                {
                    "name": loan.name,
                    "amount": float(loan.remaining_balance),
                    "due_date": str(loan.due_date) if loan.due_date else None,
                }
                for loan in loans
                if loan.remaining_balance > 0
            ],
        }

    def calculate_health_score(self):
        """
        Calculates a Financial Health Score (0 - 100):
        1. Savings Rate Score (0 - 30 pts): >20% savings = 30 pts
        2. Debt Ratio Score (0 - 25 pts): Low debt relative to income = 25 pts
        3. Budget Discipline Score (0 - 25 pts): Stay within budgets = 25 pts
        4. Emergency Reserve Score: liquid balance covers 3+ months expenses.
        """
        today = timezone.now().date()
        date_from = today.replace(day=1)
        summary = self.get_summary(date_from=date_from, date_to=today)

        # 1. Savings Rate Score (Max 30)
        savings_rate = summary.get("savings_rate", 0)
        if savings_rate >= 30:
            savings_score = 30
        elif savings_rate >= 20:
            savings_score = 25
        elif savings_rate >= 10:
            savings_score = 15
        elif savings_rate > 0:
            savings_score = 10
        else:
            savings_score = 0

        # 2. Debt Score (Max 25)
        net_worth_data = self.get_net_worth()
        assets = net_worth_data["total_assets"]
        liabilities = net_worth_data["total_liabilities"]
        if liabilities == 0:
            debt_score = 25
        elif assets > 0:
            debt_ratio = liabilities / assets
            if debt_ratio < 0.2:
                debt_score = 22
            elif debt_ratio < 0.5:
                debt_score = 15
            elif debt_ratio < 0.8:
                debt_score = 8
            else:
                debt_score = 0
        else:
            debt_score = 0

        # 3. Budget Discipline Score (Max 25)
        from budgets.models import Budget

        user_budgets = Budget.objects.filter(user=self.user, period="monthly")
        if not user_budgets.exists():
            budget_score = 15  # Default neutral score if no budgets set
        else:
            exceeded = sum(1 for b in user_budgets if b.is_exceeded)
            total_b = user_budgets.count()
            budget_score = int(25 * (1 - (exceeded / total_b)))

        # 4. Emergency Reserve Score (Max 20)
        expense_df = self._get_expense_df()
        avg_monthly_expense = (
            float(summary["total_expenses"])
            if summary["total_expenses"] > 0
            else 1.0
        )
        liquid = net_worth_data["liquid_assets"]
        months_covered = (
            liquid / avg_monthly_expense if avg_monthly_expense > 0 else 0
        )
        if months_covered >= 6:
            reserve_score = 20
        elif months_covered >= 3:
            reserve_score = 15
        elif months_covered >= 1:
            reserve_score = 10
        else:
            reserve_score = 5

        total_score = min(
            100, savings_score + debt_score + budget_score + reserve_score
        )

        if total_score >= 85:
            grade, color = "A+", "success"
            assessment = (
                "Outstanding financial health! Excellent discipline and "
                "strong savings."
            )
        elif total_score >= 70:
            grade, color = "A", "success"
            assessment = (
                "Good financial stability. You are managing expenses well."
            )
        elif total_score >= 55:
            grade, color = "B", "info"
            assessment = (
                "Moderate financial health. Consider boosting your savings "
                "rate."
            )
        elif total_score >= 40:
            grade, color = "C", "warning"
            assessment = (
                "Needs attention. Watch out for high expenses and debt "
                "obligations."
            )
        else:
            grade, color = "F", "danger"
            assessment = (
                "High risk! Immediate reduction of expenses and debt payoff "
                "required."
            )

        return {
            "total_score": total_score,
            "grade": grade,
            "color": color,
            "assessment": assessment,
            "breakdown": {
                "savings_score": savings_score,
                "debt_score": debt_score,
                "budget_score": budget_score,
                "reserve_score": reserve_score,
            },
        }

    def get_expense_forecast(self, days=30):
        """
        Forecast spending and cash flow for the next N days.
        """
        today = timezone.now().date()
        date_from = today - timedelta(days=90)
        expense_df = self._get_expense_df(date_from=date_from, date_to=today)

        if expense_df.empty:
            avg_daily = 0.0
        else:
            daily_sums = expense_df.groupby(expense_df["date"].dt.date)[
                "amount"
            ].sum()
            avg_daily = float(daily_sums.mean())

        projected_expenses = avg_daily * days

        # Include active recurring transactions due in the forecast period
        from transactions.models import RecurringTransaction

        recurring = RecurringTransaction.objects.filter(
            user=self.user,
            active=True,
            next_due_date__gte=today,
            next_due_date__lte=today + timedelta(days=days),
        )
        recurring_sum = sum(
            float(r.amount)
            for r in recurring
            if r.transaction_type == "expense"
        )
        recurring_income = sum(
            float(r.amount)
            for r in recurring
            if r.transaction_type == "income"
        )

        total_projected_expense = projected_expenses + recurring_sum

        net_worth_data = self.get_net_worth()
        current_liquid = net_worth_data["liquid_assets"]
        projected_balance = (
            current_liquid + recurring_income - total_projected_expense
        )

        forecast_timeline = []
        cumulative_expense = 0.0
        for i in range(1, days + 1):
            future_date = today + timedelta(days=i)
            cumulative_expense += avg_daily
            forecast_timeline.append(
                {
                    "date": str(future_date),
                    "projected_daily": round(avg_daily, 0),
                    "cumulative_expense": round(cumulative_expense, 0),
                }
            )

        return {
            "avg_daily_expense": round(avg_daily, 0),
            "days": days,
            "projected_expense": round(total_projected_expense, 0),
            "projected_income": round(recurring_income, 0),
            "current_liquid_balance": round(current_liquid, 0),
            "projected_end_balance": round(projected_balance, 0),
            "timeline": forecast_timeline,
        }

    def get_financial_calendar(self, days_ahead=60):
        """
        Generate a calendar of bills, debts, recurring expenses, and goals.
        """
        today = timezone.now().date()
        future_limit = today + timedelta(days=days_ahead)
        calendar_events = []

        # 1. Recurring Transactions
        from transactions.models import RecurringTransaction

        recurring = RecurringTransaction.objects.filter(
            user=self.user,
            active=True,
            next_due_date__gte=today,
            next_due_date__lte=future_limit,
        )
        for item in recurring:
            item_type = "Income" if item.transaction_type == "income" else "Bill"
            calendar_events.append(
                {
                    "id": f"rec_{item.id}",
                    "title": f"{item_type}: {item.title}",
                    "amount": float(item.amount),
                    "date": str(item.next_due_date),
                    "type": item.transaction_type,
                    "category": (
                        item.category.name if item.category else "Recurring"
                    ),
                    "icon": "bi-arrow-repeat",
                    "badge_class": (
                        "success"
                        if item.transaction_type == "income"
                        else "danger"
                    ),
                }
            )

        # 2. Debts & Loans Due
        from debts.models import Debt

        debts = Debt.objects.filter(
            user=self.user, due_date__gte=today, due_date__lte=future_limit
        )
        for debt in debts:
            if debt.remaining_balance > 0:
                calendar_events.append(
                    {
                        "id": f"debt_{debt.id}",
                        "title": f"Debt Due: {debt.name}",
                        "amount": float(debt.remaining_balance),
                        "date": str(debt.due_date),
                        "type": "debt",
                        "category": "Debt Payment",
                        "icon": "bi-exclamation-octagon",
                        "badge_class": "warning",
                    }
                )

        # 3. Savings Goals Target Dates
        from goals.models import FinancialGoal

        goals = FinancialGoal.objects.filter(
            user=self.user,
            is_completed=False,
            target_date__gte=today,
            target_date__lte=future_limit,
        )
        for goal in goals:
            calendar_events.append(
                {
                    "id": f"goal_{goal.id}",
                    "title": f"Goal Deadline: {goal.name}",
                    "amount": float(goal.remaining_amount),
                    "date": str(goal.target_date),
                    "type": "goal",
                    "category": "Savings Goal",
                    "icon": "bi-flag",
                    "badge_class": "info",
                }
            )

        calendar_events.sort(key=lambda x: x["date"])
        return calendar_events
