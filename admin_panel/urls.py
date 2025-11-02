from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    path('users/', views.users, name='admin_users'),
    path("user_status/<str:id>/", views.user_status, name="user_status"),
    path('users/search/', views.users_search, name='users_search'),
    path('order-manage/', views.admin_order, name='admin_order'),
    path('order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('order-details/<int:order_id>/', views.admin_order_details, name='admin_order_details'),
]