from django.urls import path
from . import views



urlpatterns = [
    # Admin wallet management
    path('admin-management/', views.AdminWalletListView, name='admin_wallet'),

    # User-side wallet
    path('', views.wallet_view, name='wallet'),

] 