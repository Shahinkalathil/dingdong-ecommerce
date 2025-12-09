from django.urls import path
from . import views

urlpatterns = [
    path('', views.OverView, name='profile'),
    path("edit-profile/<int:id>/", views.ProfileUpdateView, name="edit_profile"),
    path("change-password/", views.ChangePasswordView, name="change_password"),
    path('profile/address/add/', views.AddressCreateView, name='add_address'),
    path('profile/address/delete/<int:address_id>/', views.AddressDeleteView, name='delete_address'),
    path('profile/address/edit/<int:address_id>/', views.AddressUpdateView, name='edit_address'),
    path('profile/address/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
]