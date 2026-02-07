from django.urls import path
from . import views

urlpatterns = [
    # order admin
    path('admin-management/', views.AdminOrderListView, name='admin_order'),
    path('admin-management/update-status/<int:order_id>/', views.AdminOrderUpdateStatusView, name='update_order_status'),
    path('admin-management/order-details/<int:order_id>/', views.AdminOrderDetailView, name='admin_order_details'),
    # Order user
    path("list/", views.order, name="order"),
    path("detail/<str:order_number>/", views.order_detail, name='order_detail'),
    path("<str:order_number>/cancel/", views.cancel_order, name='cancel_order'),
    path('<str:order_number>/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),
    path("<str:order_number>/return/", views.request_return, name='request_return'),
    path("<str:order_number>/item/<int:item_id>/return/", views.request_item_return, name='request_item_return'),
    path('order_doc/<str:order_number>/', views.download_invoice, name='download_invoice'),
    path('order_doc/<str:order_number>/pdf/', views.generate_pdf, name='generate_pdf'),
]