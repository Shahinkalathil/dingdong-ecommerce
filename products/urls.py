from django.urls import path
from . import views


urlpatterns = [
    # Amin product management
    path('admin-management',views.AdminProductListView, name='admin_products'),
    path('admin-management/create', views.AdminProductCreateView, name='add_products'),
    path("admin-management/search/", views.AdminProductsearchView, name="products_search"),
    path('admin-management/update/<int:product_id>/', views.AdminProductUpdateView, name='edit_products'),
    path("admin-management/detail/<int:id>/", views.AdminProductDetailView, name="product_variant"), 
    path('admin-management/variant/delete/<int:variant_id>/', views.AdminProductVariantDeleteView, name='delete_variant'),

    # User-side product 
    path('', views.products, name='products'),
    path('details/<int:product_id>/', views.product_detail, name='product_detail'),
]