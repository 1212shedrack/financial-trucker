from django.urls import path
from . import views

urlpatterns = [
    path('', views.AccountListView.as_view(), name='account_list'),
    path('add/', views.AccountCreateView.as_view(), name='account_create'),
    path('<int:pk>/edit/', views.AccountUpdateView.as_view(), name='account_edit'),
    path('<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('<int:pk>/activate/', views.AccountActivateView.as_view(), name='account_activate'),
    path('transfers/', views.TransferListView.as_view(), name='transfer_list'),
    path('transfers/new/', views.TransferCreateView.as_view(), name='transfer_create'),
    path('transfers/<int:pk>/delete/', views.TransferDeleteView.as_view(), name='transfer_delete'),
]
