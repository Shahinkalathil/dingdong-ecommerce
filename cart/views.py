from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Cart, CartItem
from products.models import ProductVariant
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from offers.utils import get_offer_details

@login_required
def add_to_cart(request, product_variant_id):
    try:
        variant = get_object_or_404(ProductVariant, id=product_variant_id, is_listed=True)
        
        if not variant.product.is_listed or not variant.product.category.is_listed or not variant.product.brand.is_listed:
            messages.error(request, 'Product not available.')
            return redirect('products')
        
        if variant.stock < 1:
            messages.error(request, 'Out of stock.')
            return redirect('product_detail', variant_id=variant.id)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item = CartItem.objects.filter(cart=cart, variant=variant).first()
        
        if cart_item:
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
        else:
            CartItem.objects.create(cart=cart, variant=variant, quantity=1)
            messages.success(request, 'Added to cart.')
        return redirect('product_detail', variant_id=variant.id)
        
    except ProductVariant.DoesNotExist:
        return redirect('products')
    except Exception as e:
        return redirect('products')


def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        'variant__product__brand',
        'variant__product__category',
        'variant__product__product_offer',
        'variant__product__brand__brand_offer'
    ).prefetch_related('variant__images').all()
    
    subtotal = Decimal('0.00')
    total_discount = Decimal('0.00')
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
        
        # Get original price
        item.original_price = item.variant.price
        
        # Get best offer price, discount, and type
        item.discounted_price, item.discount_percentage, item.offer_type = get_offer_details(
            item.variant.product, 
            item.original_price
        )
        
        # Calculate item discount and subtotal
        if item.discount_percentage > 0:
            discount_amount = item.original_price - item.discounted_price
            item.item_discount = discount_amount * item.quantity
            total_discount += item.item_discount
        else:
            item.item_discount = Decimal('0.00')
        
        # Item subtotal (after discount)
        item.item_subtotal = item.discounted_price * item.quantity
        subtotal += item.item_subtotal
        
        if not item.stock_available:
            has_out_of_stock = True
        if not item.is_available:
            has_unlisted = True

    # Final total = subtotal + delivery
    total = subtotal 
    
    can_checkout = not (has_out_of_stock or has_unlisted) and cart_items.exists()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total_discount': total_discount,
        'total': total,
        'total_items': total_items,
        'can_checkout': can_checkout,
        'has_out_of_stock': has_out_of_stock,
        'has_unlisted': has_unlisted,
    }
    return render(request, 'user_side/cart/cart.html', context)


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
        
        original_price = cart_item.variant.price
        discounted_price, discount_percentage, offer_type = get_offer_details(
            cart_item.variant.product,
            original_price
        )
        item_subtotal = discounted_price * cart_item.quantity
        cart = cart_item.cart
        cart_items = cart.items.select_related(
            'variant__product__brand',
            'variant__product__category',
            'variant__product__product_offer',
            'variant__product__brand__brand_offer'
        ).all()
        
        subtotal = Decimal('0.00')
        for item in cart_items:
            item_price, _, _ = get_offer_details(
                item.variant.product,
                item.variant.price
            )
            subtotal += item_price * item.quantity
        
        total_items = cart.get_total_items()
        
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
                'can_checkout': can_checkout,
                'original_price': float(original_price),
                'discounted_price': float(discounted_price),
                'discount_percentage': float(discount_percentage)
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
        cart_items = cart.items.select_related(
            'variant__product__brand',
            'variant__product__category',
            'variant__product__product_offer',
            'variant__product__brand__brand_offer'
        ).all()
        
        subtotal = Decimal('0.00')
        for item in cart_items:
            item_price, _, _ = get_offer_details(
                item.variant.product,
                item.variant.price
            )
            subtotal += item_price * item.quantity
        
        total_items = cart.get_total_items()
        is_empty = not cart_items.exists()
        can_checkout = True
        if not is_empty:
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