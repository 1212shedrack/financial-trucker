from django.urls import path
from . import views

urlpatterns = [
    path('', views.GoalListView.as_view(), name='goal_list'),
    path('add/', views.GoalCreateView.as_view(), name='goal_create'),
    path('<int:pk>/', views.GoalDetailView.as_view(), name='goal_detail'),
    path('<int:pk>/edit/', views.GoalUpdateView.as_view(), name='goal_edit'),
    path('<int:pk>/delete/', views.GoalDeleteView.as_view(), name='goal_delete'),
    path('<int:pk>/contribute/', views.GoalContributeView.as_view(), name='goal_contribute'),
    path('<int:pk>/complete/', views.GoalMarkCompleteView.as_view(), name='goal_complete'),
]
