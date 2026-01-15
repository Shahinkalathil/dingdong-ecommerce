from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from cart.models import Cart
from profiles.utils import get_user_addresses, get_default_address
from profiles.models import Address
from orders.models import Order, OrderItem, OrderAddress
import razorpay
from django.conf import settings


def checkout(request):
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
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'user_side/checkout/checkout.html', context)


@require_POST
@transaction.atomic
def place_order(request):
    try:
        payment_method = request.POST.get('payment_method', 'cod')
        
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('variant__product').all()

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('checkout')

        default_address = get_default_address(request.user)
        if not default_address:
            messages.error(request, 'Please add a delivery address.')
            return redirect('checkout')

        subtotal = cart.get_total_price()
        delivery_charge = 0 if subtotal >= 500 else 40
        total = subtotal + delivery_charge
        
        # Check stock availability
        for cart_item in cart_items:
            if cart_item.variant.stock < cart_item.quantity:
                messages.error(request, f'Insufficient stock for {cart_item.variant.product.name}')
                return redirect('checkout')

        # Handle Razorpay payment
        if payment_method == 'online':
            try:
                # Create Order immediately with Pending status
                order = Order.objects.create(
                    user=request.user,
                    address=default_address,
                    subtotal=subtotal,
                    delivery_charge=delivery_charge,
                    total_amount=total,
                    payment_method=payment_method,
                    order_status='pending',  # Initial status for online payment
                    payment_status='pending',
                    is_paid=False
                )

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
                    # Stock is NOT deducted here for online payments. 
                    # It will be deducted in payment_success.

                # Clear cart
                cart.items.all().delete()

                # Initialize Razorpay
                key_id = settings.RAZORPAY_KEY_ID.strip()
                key_secret = settings.RAZORPAY_KEY_SECRET.strip()
                razorpay_client = razorpay.Client(auth=(key_id, key_secret))
                
                # Create Razorpay order
                amount_in_paise = int(total * 100)
                razorpay_order = razorpay_client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'payment_capture': '1',
                    'notes': {
                        'order_id': order.id, # Internal Order ID
                    }
                })
                
                # Update order with Razorpay Order ID
                order.razorpay_order_id = razorpay_order['id']
                order.save()
                
                # Redirect to payment page with internal Order ID
                return redirect('razorpay_payment', order_id=order.id)
                
            except Exception as e:
                print(f"Razorpay order creation failed: {str(e)}")
                messages.error(request, 'Payment gateway error. Please try again.')
                if 'order' in locals():
                    order.delete() # Clean up if partial failure (though transaction.atomic handles DB)
                return redirect('checkout')

        # Handle COD - Create order immediately
        order = Order.objects.create(
            user=request.user,
            address=default_address,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total_amount=total,
            payment_method=payment_method,
            order_status='confirmed',
            payment_status='pending',
            is_paid=False
        )

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

            variant.stock -= cart_item.quantity
            variant.save()
            
        cart.items.all().delete()
        messages.success(request, 'Order placed successfully!')
        return redirect('order_success', order_id=order.id)
        
    except Cart.DoesNotExist:
        messages.error(request, 'Cart not found.')
        return redirect('checkout')
    except Exception as e:
        import traceback
        print(f"Order placement error: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, 'An error occurred while placing your order.')
        return redirect('checkout')


def razorpay_payment(request, order_id=None):
    """Display Razorpay payment page"""
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        razorpay_order_id = order.razorpay_order_id
        amount = order.total_amount
        amount_in_paise = int(amount * 100)
    else:
        # Fallback for old session-based flow (if any) or error
        messages.error(request, 'Invalid payment request.')
        return redirect('checkout')
    
    context = {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID.strip(),
        'razorpay_order_id': razorpay_order_id,
        'amount': amount,
        'amount_in_paise': amount_in_paise,
        'user': request.user,
        'order_id': order.id # For failure redirection
    }
    return render(request, 'user_side/checkout/razorpay_payment.html', context)


@csrf_exempt
@require_POST
@transaction.atomic
def payment_success(request):
    """Handle successful Razorpay payment"""
    try:
        # Get payment details
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        # Verify payment signature
        key_id = settings.RAZORPAY_KEY_ID.strip()
        key_secret = settings.RAZORPAY_KEY_SECRET.strip()
        razorpay_client = razorpay.Client(auth=(key_id, key_secret))
        
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Update existing Order
        order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        
        # Check stock and deduct
        with transaction.atomic():
            for item in order.items.all():
                variant = item.variant
                if variant.stock < item.quantity:
                    # Stock run out during payment!
                    # Ideally initiate refund here. For now, mark as failed/error
                    messages.error(request, f'Sorry, {variant.product.name} went out of stock.')
                    order.payment_status = 'failed' # Or 'refund_required'
                    order.save()
                    return redirect('order_detail', order_id=order.id)
                
                variant.stock -= item.quantity
                variant.save()
        
        order.payment_status = 'paid'
        order.order_status = 'confirmed' # Confirm the order
        order.is_paid = True
        order.razorpay_payment_id = razorpay_payment_id
        order.save()
        
        messages.success(request, 'Payment successful! Order confirmed.')
        return redirect('order_success', order_id=order.id)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found for this payment.')
        return redirect('checkout')
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, 'Payment verification failed.')
        # Could mark as failed here if we can map back to order
        return redirect('checkout') # Or redirect to order details with failure
    except Exception as e:
        print(f"Payment verification failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        messages.error(request, 'Payment verification failed.')
        return redirect('checkout')


def payment_failed(request):
    """Handle payment failure notification from frontend"""
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order.payment_status = 'failed'
            order.save()
            messages.error(request, 'Payment failed. You can retry from order details.')
            return redirect('order_detail', order_number=order.order_number) # Assuming urls use order_number or id. Need to check orders/urls.py
        except Order.DoesNotExist:
            pass
    
    messages.error(request, 'Payment failed.')
    return redirect('profile') # Fallback


@transaction.atomic
def retry_payment(request, order_id):
    """Retry payment for a failed order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment_status == 'paid':
        messages.warning(request, 'This order is already paid.')
        return redirect('order_detail', order_id=order.order_number)

    try:
        # Re-initialize Razorpay (create new RZP order to be safe, or reuse if expired check needed)
        # Often easier to create a new RZP order for a retry to avoid signature issues if previous one was "attempted"
        key_id = settings.RAZORPAY_KEY_ID.strip()
        key_secret = settings.RAZORPAY_KEY_SECRET.strip()
        razorpay_client = razorpay.Client(auth=(key_id, key_secret))
        
        amount_in_paise = int(order.total_amount * 100)
        razorpay_order = razorpay_client.order.create({
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1',
            'notes': {
                'order_id': order.id,
                'retry': 'true'
            }
        })
        
        # Update order with NEW Razorpay Order ID
        order.razorpay_order_id = razorpay_order['id']
        order.save()
        
        return redirect('razorpay_payment', order_id=order.id)
        
    except Exception as e:
        print(f"Retry payment failed: {str(e)}")
        messages.error(request, 'Could not initiate retry. Please contact support.')
        return redirect('order_detail', order_id=order.order_number)


def order_success(request, order_id):
    """Display order success page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user_side/checkout/order_success.html', context)


def set_default_address(request, address_id):
    """Set an address as default"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    
    next_url = request.GET.get('next', 'checkout')
    messages.success(request, 'Default address updated successfully!')
    return redirect(next_url)