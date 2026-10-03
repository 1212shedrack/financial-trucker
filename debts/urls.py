from django.urls import path
from . import views

urlpatterns = [
    path('', views.DebtListView.as_view(), name='debt_list'),
    path('add/', views.DebtCreateView.as_view(), name='debt_create'),
    path('<int:pk>/', views.DebtDetailView.as_view(), name='debt_detail'),
    path('<int:pk>/edit/', views.DebtUpdateView.as_view(), name='debt_edit'),
    path('<int:pk>/delete/', views.DebtDeleteView.as_view(),
         name='debt_delete'),
    path('<int:pk>/repay/', views.DebtRepaymentView.as_view(),
         name='debt_repay'),
    path('<int:pk>/repay/check/', views.DebtRepaymentCheckView.as_view(),
         name='debt_repay_check'),
]
