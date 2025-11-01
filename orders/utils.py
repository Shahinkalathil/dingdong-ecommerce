from .models import Order, OrderItem, OrderAddress
from django.core.exceptions import ObjectDoesNotExist


def get_user_orders(user):
    """
    Return all orders for a specific user (latest first).
    """
    return Order.objects.filter(user=user).order_by('-created_at')


def get_order_by_number(order_number):
    """
    Return a single order by its order_number.
    Raises ObjectDoesNotExist if not found.
    """
    try:
        return Order.objects.get(order_number=order_number)
    except ObjectDoesNotExist:
        return None


def get_order_items(order):
    """
    Return all items for a given order.
    """
    return OrderItem.objects.filter(order=order)


def get_order_address(order):
    """
    Return the delivery address (OrderAddress) for a given order.
    """
    try:
        return OrderAddress.objects.get(order=order)
    except ObjectDoesNotExist:
        return None
