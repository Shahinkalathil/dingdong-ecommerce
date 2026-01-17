from django.urls import path
from . import views

urlpatterns = [
    path("toggle/<int:variant_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("check/<int:variant_id>/", views.check_wishlist, name="check_wishlist"),
]