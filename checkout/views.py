from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from django.db import models
from cart.models import Cart
from profiles.utils import get_user_addresses, get_default_address
from profiles.models import Address
from orders.models import Order, OrderItem, OrderAddress
from wallet.models import Wallet, WalletTransaction
from coupons.models import Coupon, CouponUsage
from offers.utils import get_offer_details
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

    for item in cart_items:
        item.first_image = item.variant.images.first()

    addresses = get_user_addresses(request.user)
    default_address = get_default_address(request.user)

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    subtotal_before_offer = Decimal('0')
    subtotal_after_offer = Decimal('0')
    total_offer_discount = Decimal('0')
    has_offer = False

    for item in cart_items:
        base_price = item.variant.price
        quantity = item.quantity

        final_price, discount_percentage, offer_type = get_offer_details(
            item.variant.product, 
            base_price
        )

        item_subtotal_before = base_price * quantity
        item_subtotal_after = final_price * quantity
        item_offer_discount = item_subtotal_before - item_subtotal_after
        
        item.base_price = base_price
        item.final_price = final_price
        item.offer_discount_percentage = discount_percentage
        item.offer_type = offer_type
        item.item_offer_discount = item_offer_discount
        item.subtotal_before_offer = item_subtotal_before
        item.subtotal_after_offer = item_subtotal_after

        subtotal_before_offer += item_subtotal_before
        subtotal_after_offer += item_subtotal_after
        
        if discount_percentage > 0:
            has_offer = True
            total_offer_discount += item_offer_discount
    
    subtotal = subtotal_after_offer
    delivery_charge = Decimal('0') if subtotal >= 500 else Decimal('40')
    free_delivery = max(Decimal('0'), Decimal('500') - subtotal)

    coupon_discount = Decimal(request.session.get('coupon_discount', '0'))
    coupon_code = request.session.get('coupon_code', None)

    total_before_discount = subtotal + delivery_charge
    total = total_before_discount - coupon_discount

    now = timezone.now()
    used_coupon_ids = CouponUsage.objects.filter(user=request.user).values_list('coupon_id', flat=True)
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now
    ).filter(
        models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now)
    ).exclude(
        id__in=used_coupon_ids
    ).order_by('-discount_percentage')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'wallet': wallet,
        'subtotal_before_offer': subtotal_before_offer,
        'subtotal': round(subtotal, 2),
        'total_offer_discount': round(total_offer_discount, 2),
        'delivery_charge': delivery_charge,
        'total': round(total, 2),
        'total_before_discount': total_before_discount,
        'coupon_discount': coupon_discount,
        'coupon_code': coupon_code,
        'free_delivery': round(free_delivery, 2),
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'has_offer': has_offer,
        'available_coupons': available_coupons,
        'cod_disabled': total > 1000,  
    }
    return render(request, 'user_side/checkout/checkout.html', context)


@require_POST
def apply_coupon(request):
    """Apply coupon code"""
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    
    if not coupon_code:
        return JsonResponse({'success': False, 'message': 'Please enter a coupon code'})
    
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('variant__product__brand').all()

        has_offer = False
        for item in cart_items:
            _, discount_percentage, offer_type = get_offer_details(
                item.variant.product, 
                item.variant.price
            )
            if discount_percentage > 0:
                has_offer = True
                break
        
        if has_offer:
            return JsonResponse({
                'success': False, 
                'message': 'Coupon cannot be applied when product/brand offers are active'
            })
        
        now = timezone.now()
        coupon = Coupon.objects.get(
            code=coupon_code,
            is_active=True,
            valid_from__lte=now
        )
        if coupon.valid_until and coupon.valid_until < now:
            return JsonResponse({'success': False, 'message': 'This coupon has expired'})
        if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
            return JsonResponse({'success': False, 'message': 'You have already used this coupon'})

        if coupon.usage_limit > 0:
            usage_count = CouponUsage.objects.filter(coupon=coupon).count()
            if usage_count >= coupon.usage_limit:
                return JsonResponse({'success': False, 'message': 'This coupon has reached its usage limit'})
        
        subtotal = cart.get_total_price()
        delivery_charge = Decimal('0') if subtotal >= 500 else Decimal('40')
        total_before_discount = subtotal + delivery_charge

        if subtotal < coupon.min_purchase_amount:
            return JsonResponse({
                'success': False, 
                'message': f'Minimum purchase of ₹{coupon.min_purchase_amount} required for this coupon'
            })

        discount_amount = (total_before_discount * Decimal(coupon.discount_percentage)) / Decimal('100')
        if coupon.max_discount_amount and discount_amount > coupon.max_discount_amount:
            discount_amount = coupon.max_discount_amount

        request.session['coupon_code'] = coupon_code
        request.session['coupon_discount'] = str(discount_amount)
        request.session['coupon_id'] = coupon.id
        
        total = total_before_discount - discount_amount
        
        return JsonResponse({
            'success': True,
            'message': f'Coupon "{coupon_code}" applied successfully!',
            'discount': str(discount_amount),
            'total': str(total),
            'discount_percentage': coupon.discount_percentage
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code'})
    except Exception as e:
        print(f"Coupon application error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': 'An error occurred while applying the coupon'})


@require_POST
def remove_coupon(request):
    """Remove applied coupon"""
    try:
        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)
        request.session.pop('coupon_id', None)

        cart = Cart.objects.get(user=request.user)

        subtotal = Decimal('0')
        for item in cart.items.select_related('variant__product__brand').all():
            final_price, _, _ = get_offer_details(item.variant.product, item.variant.price)
            subtotal += final_price * item.quantity
        
        delivery_charge = Decimal('0') if subtotal >= 500 else Decimal('40')
        total = subtotal + delivery_charge
        
        return JsonResponse({
            'success': True,
            'message': 'Coupon removed successfully',
            'total': str(total)
        })
    except Exception as e:
        print(f"Coupon removal error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'An error occurred'})


@require_POST
@transaction.atomic
def place_order(request):
    try:
        payment_method = request.POST.get('payment_method', 'cod')
        
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('variant__product__brand').all()

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('checkout')

        default_address = get_default_address(request.user)
        if not default_address:
            messages.error(request, 'Please add a delivery address.')
            return redirect('checkout')

        subtotal = Decimal('0')
        for item in cart_items:
            final_price, _, _ = get_offer_details(item.variant.product, item.variant.price)
            subtotal += final_price * item.quantity
        
        delivery_charge = Decimal('0') if subtotal >= 500 else Decimal('40')

        coupon_discount = Decimal(request.session.get('coupon_discount', '0'))
        coupon_id = request.session.get('coupon_id', None)
        
        total = subtotal + delivery_charge - coupon_discount

        if payment_method == 'cod' and total > 1000:
            messages.error(request, 'Cash on Delivery is not available for orders above ₹1000. Please choose another payment method.')
            return redirect('checkout')

        for cart_item in cart_items:
            if cart_item.variant.stock < cart_item.quantity:
                messages.error(request, f'Insufficient stock for {cart_item.variant.product.name}')
                return redirect('checkout')

        if payment_method == 'wallet':
            wallet = Wallet.objects.get(user=request.user)
            
            if wallet.balance < total:
                messages.error(request, f'Insufficient wallet balance. Your balance: ₹{wallet.balance}, Required: ₹{total}')
                return redirect('checkout')

            order = Order.objects.create(
                user=request.user,
                address=default_address,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                discount_amount=coupon_discount,
                total_amount=total,
                payment_method='wallet',
                order_status='confirmed',
                payment_status='paid',
                is_paid=True
            )

            if coupon_id:
                order.coupon_code = request.session.get('coupon_code')
                order.coupon_discount = coupon_discount
                order.save()

                CouponUsage.objects.create(
                    user=request.user,
                    coupon_id=coupon_id
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

                final_price, _, _ = get_offer_details(variant.product, variant.price)
                
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=variant.product.name,
                    color_name=variant.color_name,
                    color_code=variant.color_code,
                    price=final_price,  
                    quantity=cart_item.quantity
                )
                variant.stock -= cart_item.quantity
                variant.save()
            
            wallet.balance -= total
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=total,
                transaction_type='debit'
            )
            
            cart.items.all().delete()
            request.session.pop('coupon_code', None)
            request.session.pop('coupon_discount', None)
            request.session.pop('coupon_id', None)
            
            messages.success(request, 'Order placed successfully using wallet!')
            return redirect('order_success', order_id=order.id)

        if payment_method == 'online':
            try:
                order = Order.objects.create(
                    user=request.user,
                    address=default_address,
                    subtotal=subtotal,
                    delivery_charge=delivery_charge,
                    discount_amount=coupon_discount,
                    total_amount=total,
                    payment_method=payment_method,
                    order_status='pending',
                    payment_status='pending',
                    is_paid=False
                )

                if coupon_id:
                    order.coupon_code = request.session.get('coupon_code')
                    order.coupon_discount = coupon_discount
                    order.save()

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
                    final_price, _, _ = get_offer_details(variant.product, variant.price)
                    
                    OrderItem.objects.create(
                        order=order,
                        variant=variant,
                        product_name=variant.product.name,
                        color_name=variant.color_name,
                        color_code=variant.color_code,
                        price=final_price, 
                        quantity=cart_item.quantity
                    )

                cart.items.all().delete()

                key_id = settings.RAZORPAY_KEY_ID.strip()
                key_secret = settings.RAZORPAY_KEY_SECRET.strip()
                razorpay_client = razorpay.Client(auth=(key_id, key_secret))
                
                amount_in_paise = int(total * 100)
                razorpay_order = razorpay_client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'payment_capture': '1',
                    'notes': {
                        'order_id': order.id,
                    }
                })
                
                order.razorpay_order_id = razorpay_order['id']
                order.save()
                
                return redirect('razorpay_payment', order_id=order.id)
                
            except Exception as e:
                print(f"Razorpay order creation failed: {str(e)}")
                import traceback
                print(traceback.format_exc())
                messages.error(request, 'Payment gateway error. Please try again.')
                if 'order' in locals():
                    order.delete()
                return redirect('checkout')

        order = Order.objects.create(
            user=request.user,
            address=default_address,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            discount_amount=coupon_discount,
            total_amount=total,
            payment_method=payment_method,
            order_status='confirmed',
            payment_status='pending',
            is_paid=False
        )
        

        if coupon_id:
            order.coupon_code = request.session.get('coupon_code')
            order.coupon_discount = coupon_discount
            order.save()
            
            CouponUsage.objects.create(
                user=request.user,
                coupon_id=coupon_id
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
            final_price, _, _ = get_offer_details(variant.product, variant.price)
            
            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                color_name=variant.color_name,
                color_code=variant.color_code,
                price=final_price,
                quantity=cart_item.quantity
            )
            variant.stock -= cart_item.quantity
            variant.save()
            
        cart.items.all().delete()
        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)
        request.session.pop('coupon_id', None)
        
        messages.success(request, 'Order placed successfully!')
        return redirect('order_success', order_id=order.id)
        
    except Cart.DoesNotExist:
        messages.error(request, 'Cart not found.')
        return redirect('checkout')
    except Wallet.DoesNotExist:
        messages.error(request, 'Wallet not found.')
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
        messages.error(request, 'Invalid payment request.')
        return redirect('checkout')
    
    context = {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID.strip(),
        'razorpay_order_id': razorpay_order_id,
        'amount': amount,
        'amount_in_paise': amount_in_paise,
        'user': request.user,
        'order_id': order.id
    }
    return render(request, 'user_side/checkout/razorpay_payment.html', context)


@csrf_exempt
@require_POST
@transaction.atomic
def payment_success(request):
    """Handle successful Razorpay payment"""
    try:
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        key_id = settings.RAZORPAY_KEY_ID.strip()
        key_secret = settings.RAZORPAY_KEY_SECRET.strip()
        razorpay_client = razorpay.Client(auth=(key_id, key_secret))
        
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        order = Order.objects.get(razorpay_order_id=razorpay_order_id)

        with transaction.atomic():
            for item in order.items.all():
                variant = item.variant
                if variant.stock < item.quantity:
                    messages.error(request, f'Sorry, {variant.product.name} went out of stock.')
                    order.payment_status = 'failed'
                    order.save()
                    return redirect('order_detail', order_id=order.id)
                
                variant.stock -= item.quantity
                variant.save()

        if order.coupon_code:
            try:
                coupon = Coupon.objects.get(code=order.coupon_code)
                CouponUsage.objects.get_or_create(
                    user=request.user,
                    coupon=coupon
                )
            except Coupon.DoesNotExist:
                pass
        
        order.payment_status = 'paid'
        order.order_status = 'confirmed'
        order.is_paid = True
        order.razorpay_payment_id = razorpay_payment_id
        order.save()

        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)
        request.session.pop('coupon_id', None)
        
        messages.success(request, 'Payment successful! Order confirmed.')
        return redirect('order_success', order_id=order.id)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found for this payment.')
        return redirect('checkout')
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, 'Payment verification failed.')
        return redirect('checkout')
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
            return redirect('order_detail', order_number=order.order_number)
        except Order.DoesNotExist:
            pass
    
    messages.error(request, 'Payment failed.')
    return redirect('profile')


@transaction.atomic
def retry_payment(request, order_id):
    """Retry payment for a failed order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment_status == 'paid':
        messages.warning(request, 'This order is already paid.')
        return redirect('order_detail', order_id=order.order_number)

    try:
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