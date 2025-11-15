from django.urls import path
from . import views



urlpatterns = [
    path('',views.admin_dash, name='admin_index'),
    path('brands/', views.admin_brands, name='admin_brands'),
    path('brands/search/', views.brands_search, name='brands_search'),
    path('brands/add/', views.add_brand, name='add_brand'),
    path('brands/edit/<int:brand_id>/', views.edit_brand, name='edit_brand'),
    path('brands/toggle/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'),
    path('brands/delete/<int:brand_id>/', views.delete_brand, name='delete_brand'),

] 