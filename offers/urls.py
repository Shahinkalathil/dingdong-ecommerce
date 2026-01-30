from django.urls import path
from . import views



urlpatterns = [
    path('admin-management/create/brand/<brand_id>/', views.AdminBrandOfferCreateView, name='add_brandoffer'),
    path('admin-management/delete/brand/<brand_id>/', views.AdminBrandOfferDeleteView, name='delete_brandoffer'),
    path('admin-management/u&b/<brand_id>/', views.AdminBrandBlockView, name='block_brandoffer'),
      path('product/<int:product_id>/offer/add/', 
         views.AdminProductOfferCreateView, 
         name='add_productoffer'),
    
    path('product/<int:product_id>/offer/toggle/', 
         views.AdminProductOfferToggleView, 
         name='toggle_productoffer'),
    
    path('product/<int:product_id>/offer/delete/', 
         views.AdminProductOfferDeleteView, 
         name='delete_productoffer'),
    

]
