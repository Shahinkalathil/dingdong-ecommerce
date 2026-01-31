from django.urls import path
from . import views



urlpatterns = [
    path('admin-management/create/brand/<brand_id>/', views.AdminBrandOfferCreateView, name='add_brandoffer'),
    path('admin-management/delete/brand/<brand_id>/', views.AdminBrandOfferDeleteView, name='delete_brandoffer'),
    path('admin-management/u&b/brand/<brand_id>/', views.AdminBrandBlockView, name='block_brandoffer'),
    path('admin-management/create/product/<int:product_id>', views.AdminProductOfferCreateView, name='add_productoffer'),
    path('admin-management/u&b/product/<int:product_id>', views.AdminProductOfferToggleView, name='toggle_productoffer'),
    path('admin-management/delete/product/<int:product_id>', views.AdminProductOfferDeleteView, name='delete_productoffer'),
]
