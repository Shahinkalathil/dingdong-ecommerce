from django.urls import path
from . import views

urlpatterns = [
    path("", views.order, name="order"),
    path("<str:order_number>/", views.order_detail, name='order_detail'),
    path("<str:order_number>/cancel/", views.cancel_order, name='cancel_order'),
    path("<str:order_number>/item/<int:item_id>/cancel/", views.cancel_order_item, name='cancel_order_item'),
    path("<str:order_number>/return/", views.request_return, name='request_return'),
    path("<str:order_number>/invoice/", views.download_invoice, name='download_invoice'),
]