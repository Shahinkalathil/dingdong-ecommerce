from django.urls import path
from . import views



urlpatterns = [
    path('', views.AdminBrandListView, name='admin_brands'),
    path('brands/search/', views.AdminBrandsearchView, name='brands_search'),
    path('create/', views.AdminBrandCreateView, name='add_brand'),
    path('update/<int:brand_id>/', views.AdminBrandUpdateView, name='edit_brand'),
    path('toggle/<int:brand_id>/', views.AdminBrandStatusView, name='toggle_brand_status'),

] 
