from django.urls import path
from . import views

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('razorpay-payment/', views.razorpay_payment, name='razorpay_payment'),
    path('razorpay-payment/<int:order_id>/', views.razorpay_payment, name='razorpay_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('retry-payment/<int:order_id>/', views.retry_payment, name='retry_payment'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('set-default-address/<int:address_id>/', views.set_default_address, name='set_default_address'),
]