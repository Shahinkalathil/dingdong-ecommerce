from django.urls import path
from . import views

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path('set-default-address/<int:address_id>/', views.set_default_address, name='set_default_address'),
]



