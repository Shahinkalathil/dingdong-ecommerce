from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', views.user_logout, name='logout'),
    path('products/', views.products, name='products'),
    path("products/details/<int:product_id>/", views.product_detail, name="product_detail")

]
