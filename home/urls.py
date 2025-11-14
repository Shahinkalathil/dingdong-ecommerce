from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', views.user_logout, name='logout'),
    path('products/', views.products, name='products'),
    path('products/details/<int:product_id>/', views.product_detail, name='product_detail'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('brands/', views.brands, name='brands_list'),
    path('Repair_and_Service', views.Repair_and_Service, name="Repair_and_Service"),
    path('categories', views.categories, name='categories')
]