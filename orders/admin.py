from django.contrib import admin
from .models import OrderItem, Order, OrderAddress

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderAddress)