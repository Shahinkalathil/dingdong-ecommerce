from .models import Address
# utils.py

def get_user_addresses(user):
    """
    Return all addresses for the given user,
    ordered with the default address first.
    """
    return Address.objects.filter(user=user).order_by('-is_default', '-created_at')


def get_default_address(user):
    """
    Return the default address for the user if available.
    """
    return Address.objects.filter(user=user, is_default=True).first()