from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from cart.models import Cart
from uProfile.utils import get_user_addresses, get_default_address
from uProfile.models import Address

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Load all cart items efficiently
    cart_items = (
        cart.items
        .select_related('variant__product__brand', 'variant__product__category')
        .prefetch_related('variant__images')
        .all()
    )

    # Attach first image to each item
    for item in cart_items:
        item.first_image = item.variant.images.first()

    # Get addresses
    addresses = get_user_addresses(request.user)
    default_address = get_default_address(request.user)

    # Totals
    subtotal = cart.get_total_price()
    delivery_charge = 0
    total = subtotal + delivery_charge

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total,
    }

    return render(request, 'user_side/checkout/checkout.html', context)

@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    # Remove default from other addresses
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

    # Set the clicked one as default
    address.is_default = True
    address.save()

    # Redirect back to the page user came from (checkout or profile)
    next_url = request.GET.get('next', 'checkout')
    return redirect(next_url)