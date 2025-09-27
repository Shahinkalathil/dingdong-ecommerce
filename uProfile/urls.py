from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='profile'),
    path('edit/', views.edit_profile, name="edit_profile"),
    path("address/add/", views.add_address, name="add_address"),
    path("address/edit/", views.edit_address, name="edit_address"),



    path("orders/", views.order, name="order"),
    path("order_detail", views.order_detail, name='order_detail')
]