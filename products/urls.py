from django.urls import path
from . import views


urlpatterns = [
    # Amin product management
    path('',views.AdminProductListView, name='admin_products'),
    path('create', views.AdminProductCreateView, name='add_products'),
    path("search/", views.AdminProductsearchView, name="products_search"),
    path('update/<int:product_id>/', views.AdminProductUpdateView, name='edit_products'),
    path("detail/<int:id>/", views.AdminProductDetailView, name="product_variant"),  
]