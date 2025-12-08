from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='profile'),
    path("edit-profile/<int:id>/", views.edit_profile, name="edit_profile"),
    path("change-password/", views.change_password, name="change_password"),
    path('profile/address/add/', views.add_address, name='add_address'),
    path('profile/address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('profile/address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('profile/address/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
    
]