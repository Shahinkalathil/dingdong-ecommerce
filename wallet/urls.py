from django.urls import path
from . import views



urlpatterns = [
    # Admin payment management
    path('admin-payment-management/', views.AdminPaymentListView, name='admin_payment_management'),
    path('admin-payment-detail/<str:payment_type>/<int:payment_id>/', views.AdminPaymentDetailView, name='admin_payment_detail'),

    
    # User-side wallet
    path('', views.wallet_view, name='wallet'),

] 