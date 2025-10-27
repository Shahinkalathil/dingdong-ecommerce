from django.shortcuts import render, get_object_or_404
from cart.models import Cart

def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Load all related data efficiently
    cart_items = (
        cart.items
        .select_related('variant__product__brand', 'variant__product__category')
        .prefetch_related('variant__images')
        .all()
    )

    # Attach first image to each item
    for item in cart_items:
        item.first_image = item.variant.images.first()

    # Calculate totals
    subtotal = cart.get_total_price()
    delivery_charge = 0  # you can change later
    total = subtotal + delivery_charge

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total,
    }

    return render(request, 'user_side/checkout/checkout.html', context)