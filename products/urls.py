from django.urls import path
from . import views


urlpatterns = [
    path('',views.admin_products, name='admin_products'),
    path('add_products', views.add_products, name='add_products'),
    path("products_search/", views.products_search, name="products_search"),
    path('edit_products/<int:product_id>/', views.edit_products, name='edit_products'),
    path("product-variant/<int:id>/", views.product_variant, name="product_variant"),
    path('category/', views.categories, name='admin_category'),
    path('category/search/', views.categories_search, name='categories_search'),
    path('category_status/<int:id>/<str:action>/', views.category_status, name='category_status'),   
]