from django.urls import path
from . import views

urlpatterns = [
    path('', views.BudgetListView.as_view(), name='budget_list'),
    path('add/', views.BudgetCreateView.as_view(), name='budget_create'),
    path('<int:pk>/', views.BudgetDetailView.as_view(), name='budget_detail'),
    path('<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='budget_edit'),
    path('<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='budget_delete'),
]
