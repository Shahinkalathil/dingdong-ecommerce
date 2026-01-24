from django.urls import path
from . import views

urlpatterns = [
    # Coupon management
    path('admin-management/', views.AdminCouponsListView, name='admin_coupons'),
    path('admin-management/create/', views.AdminCouponsCreateView, name='add_coupons'),
    path('admin-management/update/<int:coupon_id>/', views.AdminCouponsUpdateView, name='edit_coupons'),
    path('admin-management/toggle-status/<int:coupon_id>/', views.AdminCouponsToggleStatusView, name='toggle_coupon_status'),
    path('admin-management/search/', views.AdminCouponsSearchView, name='coupon_search'),
]