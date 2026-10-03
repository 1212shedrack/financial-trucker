from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/read/', views.NotificationMarkReadView.as_view(), name='notification_read'),
    path('<int:pk>/delete/', views.NotificationDeleteView.as_view(), name='notification_delete'),
    path('mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('api/', views.NotificationAPIView.as_view(), name='notification_api'),
]
