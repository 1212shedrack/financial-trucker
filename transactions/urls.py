from django.urls import path
from . import views

urlpatterns = [
    # Combined transactions
    path('', views.TransactionListView.as_view(), name='transaction_list'),
    # Income
    path('income/', views.IncomeListView.as_view(), name='income_list'),
    path('income/add/', views.IncomeCreateView.as_view(), name='income_create'),
    path('income/<int:pk>/', views.IncomeDetailView.as_view(), name='income_detail'),
    path('income/<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income_edit'),
    path('income/<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income_delete'),
    # Expenses
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    # Recurring
    path('recurring/', views.RecurringListView.as_view(), name='recurring_list'),
    path('recurring/add/', views.RecurringCreateView.as_view(), name='recurring_create'),
    path('recurring/<int:pk>/edit/', views.RecurringUpdateView.as_view(), name='recurring_edit'),
    path('recurring/<int:pk>/delete/', views.RecurringDeleteView.as_view(), name='recurring_delete'),
    path('recurring/<int:pk>/toggle/', views.RecurringToggleView.as_view(), name='recurring_toggle'),
]
