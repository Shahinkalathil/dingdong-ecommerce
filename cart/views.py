from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Cart, CartItem
from products.models import ProductVariant
from django.contrib.auth.decorators import login_required

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

@login_required
def add_to_cart(request, product_variant_id):
    """
    Add product variant to cart
    Shows appropriate messages and redirects back to product detail page
    """
    try:
        variant = get_object_or_404(ProductVariant, id=product_variant_id, is_listed=True)
        
        # Check if product, category, and brand are listed
        if not variant.product.is_listed or not variant.product.category.is_listed or not variant.product.brand.is_listed:
            messages.error(request, 'Product not available.')
            return redirect('products')
        
        # Check stock
        if variant.stock < 1:
            messages.error(request, 'Out of stock.')
            return redirect('product_detail', variant_id=variant.id)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if item already in cart
        cart_item = CartItem.objects.filter(cart=cart, variant=variant).first()
        
        if cart_item:
            # Item already in cart - check if we can increase quantity
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, 'Quantity updated.')
            else:
                messages.warning(request, f'Only {variant.stock} available.')
        else:
            # Add new item to cart
            CartItem.objects.create(cart=cart, variant=variant, quantity=1)
            messages.success(request, 'Added to cart.')
        
        # Redirect back to the same product variant page
        return redirect('product_detail', variant_id=variant.id)
        
    except ProductVariant.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('products')
    except Exception as e:
        print(f"Error in add_to_cart: {e}")
        messages.error(request, 'Something went wrong.')
        return redirect('products')


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
    
