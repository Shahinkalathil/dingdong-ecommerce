from django.urls import path
from . import views


urlpatterns = [
    # Amin product management
    path('',views.AdminProductListView, name='admin_products'),
    path('create', views.AdminProductCreateView, name='add_products'),
    path("search/", views.AdminProductsearchView, name="products_search"),
    path('update/<int:product_id>/', views.AdminProductUpdateView, name='edit_products'),
    path("detail/<int:id>/", views.AdminProductDetailView, name="product_variant"),



    path('category/', views.categories, name='admin_category'),
    path('category/search/', views.categories_search, name='categories_search'),
    path('category_status/<int:id>/<str:action>/', views.category_status, name='category_status'),   
]