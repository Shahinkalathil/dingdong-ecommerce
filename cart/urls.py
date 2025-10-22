from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/checkout/', views.checkout, name='checkout'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
]