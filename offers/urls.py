from django.urls import path
from . import views



urlpatterns = [
    path('admin-management/create/brand/<brand_id>/', views.AdminBrandOfferCreateView, name='add_brandoffer'),
    path('admin-management/delete/brand/<brand_id>/', views.AdminBrandOfferDeleteView, name='delete_brandoffer'),
    path('admin-management/u&b/<brand_id>/', views.AdminBrandBlockView, name='block_brandoffer'),

]