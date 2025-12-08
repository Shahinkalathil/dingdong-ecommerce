from django.urls import path
from . import views



urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('admin-management/', views.AdminUserListView, name='admin_users'),
    path("admin-management/user_status/<str:id>/", views.AdminUserStatusView, name="user_status"),
    path('admin-management/search/', views.AdminUserSearchView, name='users_search'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
] 