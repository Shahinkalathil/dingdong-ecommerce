from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add/<int:product_variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
]