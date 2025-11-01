from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from cart.models import Cart
from uProfile.utils import get_user_addresses, get_default_address
from uProfile.models import Address
from orders.models import Order, OrderItem, OrderAddress


def checkout(request):
    """
    Display checkout page
    """
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = (
        cart.items
        .select_related('variant__product__brand', 'variant__product__category')
        .prefetch_related('variant__images')
        .all()
    )
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    for item in cart_items:
        item.first_image = item.variant.images.first()

    addresses = get_user_addresses(request.user)
    default_address = get_default_address(request.user)

    if not default_address:
        messages.warning(request, 'Please add a delivery address.')
        return redirect('add_address')

    subtotal = cart.get_total_price()
    delivery_charge = 0 if subtotal >= 500 else 40
    free_delivery = 500 - subtotal if subtotal < 500 else 0
    total = subtotal + delivery_charge
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total': total,
        'free_delivery': free_delivery,
    }

    return render(request, 'user_side/checkout/checkout.html', context)


@require_POST
@transaction.atomic
def place_order(request):
    """
    Process order placement via AJAX - only COD supported
    """
    try:
        # Get user's cart
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('variant__product').all()

        # Validate cart is not empty
        if not cart_items:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty.'
            }, status=400)

        # Get default delivery address
        default_address = get_default_address(request.user)
        if not default_address:
            return JsonResponse({
                'success': False,
                'message': 'Please add a delivery address.'
            }, status=400)

        # Calculate totals
        subtotal = cart.get_total_price()
        delivery_charge = 0 if subtotal >= 500 else 40
        total = subtotal + delivery_charge

        # Validate stock availability
        for cart_item in cart_items:
            if cart_item.variant.stock < cart_item.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Insufficient stock for {cart_item.variant.product.name}'
                }, status=400)

        # Create the order - COD with pending payment
        order = Order.objects.create(
            user=request.user,
            address=default_address,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total_amount=total,
            payment_method='cod',
            order_status='confirmed',
            payment_status='pending',
            is_paid=False
        )
        
        # Create order address snapshot
        OrderAddress.objects.create(
            order=order,
            full_name=default_address.full_name,
            phone_number=default_address.mobile_number,
            flat_house=default_address.flat_house,
            area_street=default_address.area_street,
            landmark=default_address.landmark or '',
            town_city=default_address.town_city,
            state=default_address.state,
            pincode=default_address.pincode
        )
        
        # Create order items and update variant stock
        for cart_item in cart_items:
            variant = cart_item.variant

            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                color_name=variant.color_name,
                color_code=variant.color_code,
                price=variant.price,
                quantity=cart_item.quantity
            )

            # Reduce stock
            variant.stock -= cart_item.quantity
            variant.save()
 
        # Clear the cart
        cart.items.all().delete()

        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Order placed successfully!',
            'order': {
                'order_number': order.order_number,
                'total_amount': str(total),
            }
        })
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found.'
        }, status=404)
    except Exception as e:
        # Log error for debugging
        import traceback
        print(f"Order placement error: {str(e)}")
        print(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while placing your order. Please try again.'
        }, status=500)


def set_default_address(request, address_id):
    """Set default address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    
    next_url = request.GET.get('next', 'checkout')
    return redirect(next_url)