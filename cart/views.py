from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cart, CartItem, WishlistItem
from products.models import ProductVariant


def cart(request):
    # Get or create cart for the user
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    # Get all cart items with related data
    cart_items = cart.items.select_related(
        'variant__product__brand',
        'variant__product__category'
    ).prefetch_related('variant__images').all()
    
    # Calculate totals
    subtotal = cart.get_total_price()
    total_items = cart.get_total_items()
    
    # Check stock availability and unlisted status for each item
    has_out_of_stock = False
    has_unlisted = False
    
    for item in cart_items:
        item.stock_available = item.is_in_stock()
        item.first_image = item.variant.images.first()
        
        # Check if product or variant is unlisted
        item.is_available = (
            item.variant.is_listed and 
            item.variant.product.is_listed and
            item.variant.product.category.is_listed and
            item.variant.product.brand.is_listed
        )
        
        if not item.stock_available:
            has_out_of_stock = True
        
        if not item.is_available:
            has_unlisted = True
    
    # Disable checkout if there are issues
    can_checkout = not (has_out_of_stock or has_unlisted) and cart_items.exists()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': subtotal,
        'total_items': total_items,
        'delivery_charge': 0,
        'can_checkout': can_checkout,
        'has_out_of_stock': has_out_of_stock,
        'has_unlisted': has_unlisted,
    }
    
    return render(request, 'user_side/cart/cart.html', context)


def add_to_cart(request, product_variant_id):
    # Get the variant
    variant = get_object_or_404(ProductVariant, id=product_variant_id)
    
    # Check if variant is listed and has stock
    if not variant.is_listed or not variant.product.is_listed:
        messages.error(request, 'This product is not available.')
        return redirect('product_detail', product_id=variant.product.id)
    
    # Check if category and brand are listed
    if not variant.product.category.is_listed or not variant.product.brand.is_listed:
        messages.error(request, 'This product is currently unavailable.')
        return redirect('product_detail', product_id=variant.product.id)
    
    if variant.stock < 1:
        messages.error(request, 'This product is out of stock.')
        return redirect('product_detail', product_id=variant.product.id)
    
    # Get or create cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if item already exists in cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={'quantity': 1}
    )
    
    if not item_created:
        # Item already exists, increase quantity
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'{variant.product.name} quantity updated in cart.')
        else:
            messages.warning(request, f'Cannot add more. Only {variant.stock} items available in stock.')
    else:
        messages.success(request, f'{variant.product.name} added to cart successfully.')
    
    # Remove from wishlist if exists
    try:
        wishlist_item = WishlistItem.objects.get(
            user=request.user,
            variant=variant
        )
        wishlist_item.delete()
        messages.info(request, 'Item removed from wishlist.')
    except WishlistItem.DoesNotExist:
        pass
    
    return redirect('cart')


def checkout(request):
    # Check if cart has items and all are in stock
    cart = Cart.objects.filter(user=request.user).first()
    
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    
    # Check for out of stock or unlisted items
    for item in cart.items.all():
        if not item.is_in_stock():
            messages.error(request, f'{item.variant.product.name} is out of stock. Please update your cart.')
            return redirect('cart')
        
        if not item.variant.is_listed or not item.variant.product.is_listed:
            messages.error(request, f'{item.variant.product.name} is no longer available. Please update your cart.')
            return redirect('cart')
    
    return render(request, 'user_side/checkout/checkout.html')


def update_cart_quantity(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        # Validate action
        if action not in ['increment', 'decrement']:
            messages.error(request, 'Invalid action.')
            return redirect('cart')
        
        # Check if product is still listed
        if not cart_item.variant.is_listed or not cart_item.variant.product.is_listed:
            messages.error(request, 'This product is no longer available.')
            return redirect('cart')
        
        if action == 'increment':
            if cart_item.quantity < cart_item.variant.stock:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f'Quantity updated for {cart_item.variant.product.name}.')
            else:
                messages.warning(request, f'Cannot add more. Only {cart_item.variant.stock} items available.')
        
        
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, f'Quantity updated for {cart_item.variant.product.name}.')
            else:
                messages.warning(request, 'Quantity cannot be less than 1.')
        
        return redirect('cart')
    
    return redirect('cart')


def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.variant.product.name
        cart_item.delete()
        messages.success(request, f'{product_name} removed from cart.')
    
    return redirect('cart')