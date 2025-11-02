from .models import Order, OrderItem, OrderAddress
from django.core.exceptions import ObjectDoesNotExist


def get_user_orders(user):
    return Order.objects.filter(user=user).order_by('-created_at')


def get_order_by_number(order_number):
    try:
        return Order.objects.get(order_number=order_number)
    except ObjectDoesNotExist:
        return None


def get_order_items(order):
    return OrderItem.objects.filter(order=order)


def get_order_address(order):
    try:
        return OrderAddress.objects.get(order=order)
    except ObjectDoesNotExist:
        return None
