from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Cart, CartItem, WishlistItem
from products.models import ProductVariant


def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('variant__product__brand','variant__product__category').prefetch_related('variant__images').all()
    subtotal = cart.get_total_price()
    total_items = cart.get_total_items()
    has_out_of_stock = False
    has_unlisted = False
    for item in cart_items:
        item.stock_available = item.is_in_stock()
        item.first_image = item.variant.images.first()
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
    variant = get_object_or_404(ProductVariant, id=product_variant_id)  
    if not variant.is_listed or not variant.product.is_listed:
        messages.error(request, 'This product is not available.')
        return redirect('product_detail', product_id=variant.product.id)
    if not variant.product.category.is_listed or not variant.product.brand.is_listed:
        messages.error(request, 'This product is currently unavailable.')
        return redirect('product_detail', product_id=variant.product.id)
    if variant.stock < 1:
        messages.error(request, 'This product is out of stock.')
        return redirect('product_detail', product_id=variant.product.id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={'quantity': 1}
    )
    if not item_created:
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'{variant.product.name} quantity updated in cart.')
        else:
            messages.warning(request, f'Cannot add more. Only {variant.stock} items available in stock.')
    else:
        messages.success(request, f'{variant.product.name} added to cart successfully.')
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

@require_POST
def update_cart_quantity(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')

        if action not in ['increment', 'decrement']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action.'
            }, status=400)

        if not cart_item.variant.is_listed or not cart_item.variant.product.is_listed:
            return JsonResponse({
                'success': False,
                'message': 'This product is no longer available.'
            }, status=400)
        
        if action == 'increment':
            if cart_item.quantity < cart_item.variant.stock:
                cart_item.quantity += 1
                cart_item.save()
                message = f'Quantity updated for {cart_item.variant.product.name}.'
                message_type = 'success'
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot add more. Only {cart_item.variant.stock} items available.',
                    'message_type': 'warning'
                })
        
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                message = f'Quantity updated for {cart_item.variant.product.name}.'
                message_type = 'success'
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Quantity cannot be less than 1.',
                    'message_type': 'warning'
                })
        
        # Recalculate cart totals
        cart = cart_item.cart
        subtotal = cart.get_total_price()
        total_items = cart.get_total_items()
        item_subtotal = cart_item.get_subtotal()
        
        # Check if checkout is still possible
        cart_items = cart.items.select_related('variant__product__brand','variant__product__category').all()
        has_out_of_stock = False
        has_unlisted = False
        for item in cart_items:
            is_available = (
                item.variant.is_listed and 
                item.variant.product.is_listed and
                item.variant.product.category.is_listed and
                item.variant.product.brand.is_listed
            )
            if not item.is_in_stock():
                has_out_of_stock = True
            if not is_available:
                has_unlisted = True
        can_checkout = not (has_out_of_stock or has_unlisted) and cart_items.exists()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'message_type': message_type,
            'data': {
                'quantity': cart_item.quantity,
                'item_subtotal': float(item_subtotal),
                'subtotal': float(subtotal),
                'total': float(subtotal),
                'total_items': total_items,
                'can_increment': cart_item.quantity < cart_item.variant.stock,
                'can_decrement': cart_item.quantity > 1,
                'can_checkout': can_checkout
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }, status=500)

@require_POST
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.variant.product.name
        cart = cart_item.cart
        cart_item.delete()
        
        # Recalculate cart totals
        subtotal = cart.get_total_price()
        total_items = cart.get_total_items()
        
        # Check if cart is empty
        cart_items = cart.items.all()
        is_empty = not cart_items.exists()
        
        # Check if checkout is still possible
        can_checkout = True
        if not is_empty:
            has_out_of_stock = False
            has_unlisted = False
            for item in cart_items.select_related('variant__product__brand','variant__product__category'):
                is_available = (
                    item.variant.is_listed and 
                    item.variant.product.is_listed and
                    item.variant.product.category.is_listed and
                    item.variant.product.brand.is_listed
                )
                if not item.is_in_stock():
                    has_out_of_stock = True
                if not is_available:
                    has_unlisted = True
            can_checkout = not (has_out_of_stock or has_unlisted)
        
        return JsonResponse({
            'success': True,
            'message': f'{product_name} removed from cart.',
            'message_type': 'success',
            'data': {
                'subtotal': float(subtotal),
                'total': float(subtotal),
                'total_items': total_items,
                'is_empty': is_empty,
                'can_checkout': can_checkout
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }, status=500)