from cart.models import Cart
def get_user_cart_items(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    cart_items = (
        cart.items
        .select_related('variant__product__brand', 'variant__product__category')
        .prefetch_related('variant__images')
    )
    for item in cart_items:
        item.first_image = item.variant.images.first()
    return cart, cart_items