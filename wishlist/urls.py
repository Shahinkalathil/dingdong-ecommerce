from django.urls import path
from . import views

urlpatterns = [
    path('', views.wishlist, name='wishlist'),
    path('remove/<int:variant_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]