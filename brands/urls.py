from django.urls import path
from . import views



urlpatterns = [
    path('admin-management/', views.AdminBrandListView, name='admin_brands'),
    path('admin-management/brands/search/', views.AdminBrandsearchView, name='brands_search'),
    path('admin-management/create/', views.AdminBrandCreateView, name='add_brand'),
    path('admin-management/update/<int:brand_id>/', views.AdminBrandUpdateView, name='edit_brand'),
    path('admin-management/toggle/<int:brand_id>/', views.AdminBrandStatusView, name='toggle_brand_status'),

] 
