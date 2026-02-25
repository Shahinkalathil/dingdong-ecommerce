from datetime import datetime, timedelta
import json
from offers.utils import get_offer_details
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST, require_http_methods
from decimal import Decimal
from wallet.models import Wallet, WalletTransaction
from weasyprint import HTML
from .models import Order, OrderItem, OrderReturn, OrderItemReturn
from wallet.models import Wallet, WalletTransaction


# userside
@login_required
def order(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items__variant__images',
        'items__variant__product',
        'delivery_address'
    ).select_related('user', 'address')
    
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    date_range = request.GET.get('date-range', '')
    if date_range:
        today = datetime.now()
        if date_range == 'last-week':
            start_date = today - timedelta(days=7)
            orders = orders.filter(created_at__gte=start_date)
        elif date_range == 'last-month':
            start_date = today - timedelta(days=30)
            orders = orders.filter(created_at__gte=start_date)
        elif date_range == 'last-3-months':
            start_date = today - timedelta(days=90)
            orders = orders.filter(created_at__gte=start_date)
    
    paginator = Paginator(orders, 5)
    page = request.GET.get('page', 1)
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_range': date_range,
    }
    
    return render(request, 'user_side/profile/order.html', context)


# ─────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────
@login_required
def order_detail(request, order_number):
    """Display detailed order information with offer and coupon breakdown."""
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__variant__images',
            'items__variant__product__brand',
            'items__variant__product',
            'items__return_request'
        ).select_related('delivery_address', 'user', 'return_request'),
        order_number=order_number,
        user=request.user
    )

    # ── Per-item offer enrichment ──────────────────────────────────────────
    # We need the ORIGINAL (non-offer) price for each item to show savings.
    # item.price is the offer-adjusted price stored at order time.
    # item.variant.price is the current base price — use it for display only.
    active_subtotal = Decimal('0.00')  # sum of active (non-cancelled, non-returned) items
    total_offer_savings = Decimal('0.00')

    active_subtotal = Decimal('0.00')
    total_offer_savings = Decimal('0.00')

    for item in order.items.all():
        variant = item.variant
        if variant:
            base_price = variant.price
            _, discount_pct, offer_type = get_offer_details(variant.product, base_price)
            item.original_price = base_price
            item.offer_type = offer_type
            item.offer_discount_pct = discount_pct
            item.offer_saving = max((base_price - item.price) * item.quantity, Decimal('0.00'))
            item.original_subtotal = base_price * item.quantity
        else:
            item.original_price = item.price
            item.offer_type = None
            item.offer_discount_pct = Decimal('0')
            item.offer_saving = Decimal('0.00')
            item.original_subtotal = item.subtotal

        if not item.is_cancelled and not item.is_returned:
            active_subtotal += item.subtotal
            total_offer_savings += item.offer_saving

    # ── Second pass: attach proportional coupon discount per item ─────────────
    coupon_discount = order.coupon_discount or Decimal('0.00')

    for item in order.items.all():
        if not item.is_cancelled and not item.is_returned and active_subtotal > 0 and coupon_discount > 0:
            item.coupon_per_item = ((item.subtotal / active_subtotal) * coupon_discount).quantize(Decimal('0.01'))
        else:
            item.coupon_per_item = Decimal('0.00')

    # ── Coupon info ────────────────────────────────────────────────────────
    coupon_discount = order.coupon_discount or Decimal('0.00')
    coupon_code = order.coupon_code or ''

    # ── Return eligibility ─────────────────────────────────────────────────
    can_cancel = order.order_status in ['pending', 'confirmed']
    can_download_invoice = order.order_status == 'delivered'

    can_return = False
    return_days_left = 0

    if order.order_status == 'delivered':
        days_since_delivery = (timezone.now() - order.updated_at).days
        return_days_left = 7 - days_since_delivery
        if return_days_left > 0 and not hasattr(order, 'return_request'):
            can_return = True

    active_items_count = order.items.filter(is_cancelled=False, is_returned=False).count()

    status_steps = {
        'confirmed':       order.order_status in ['confirmed', 'shipped', 'out_for_delivery', 'delivered'],
        'shipped':         order.order_status in ['shipped', 'out_for_delivery', 'delivered'],
        'out_for_delivery':order.order_status in ['out_for_delivery', 'delivered'],
        'delivered':       order.order_status == 'delivered',
    }
    

    context = {
        'order': order,
        'can_cancel': can_cancel,
        'can_return': can_return,
        'can_download_invoice': can_download_invoice,
        'status_steps': status_steps,
        'coupon_discount': coupon_discount,
        'coupon_code': coupon_code,
        'total_offer_savings': total_offer_savings,
        'return_days_left': return_days_left if return_days_left > 0 else 0,
        'active_items_count': active_items_count,
        'active_subtotal': active_subtotal,
    }

    return render(request, 'user_side/profile/order_detail.html', context)


# ─────────────────────────────────────────────
# CANCEL ENTIRE ORDER
# ─────────────────────────────────────────────
@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel entire order and refund to wallet."""
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__variant'),
            order_number=order_number,
            user=request.user
        )

        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({'success': False, 'message': 'Order cannot be cancelled at this stage.'}, status=400)

        data = json.loads(request.body)
        cancel_reason = data.get('reason', 'No reason provided')

        with transaction.atomic():
            for item in order.items.all():
                if item.variant and not item.is_cancelled:
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.is_cancelled = True
                item.cancelled_at = timezone.now()
                item.item_status = 'cancelled'
                item.save()

            order.order_status = 'cancelled'
            order.cancellation_reason = cancel_reason
            order.cancelled_at = timezone.now()

            refund_amount = Decimal('0.00')
            if order.is_paid or order.payment_status == 'paid':
                refund_amount = order.total_amount
                order.payment_status = 'refunded'
                order.is_paid = False

                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet, order=order,
                    amount=refund_amount, transaction_type='credit'
                )
            else:
                order.payment_status = 'failed'
                order.is_paid = False

            order.save()

        msg = (f'Order {order_number} cancelled. ₹{refund_amount} refunded to your wallet.'
               if refund_amount > 0 else f'Order {order_number} cancelled successfully.')
        messages.success(request, msg)

        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
            'refund_amount': float(refund_amount),
            'redirect_url': '/orders/list/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error cancelling order: {str(e)}'}, status=500)


# ─────────────────────────────────────────────
# CANCEL SINGLE ITEM
# ─────────────────────────────────────────────
@login_required
@require_POST
def cancel_order_item(request, order_number, item_id):
    """
    Cancel one item and refund the proportional amount the customer paid for it.

    Refund = item.subtotal − item's proportional share of coupon_discount
           + delivery_charge if this was the last active item
    """
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__variant'),
            order_number=order_number,
            user=request.user
        )

        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({'success': False, 'message': 'Order items cannot be cancelled at this stage.'}, status=400)

        item = get_object_or_404(OrderItem, id=item_id, order=order)

        if item.is_cancelled:
            return JsonResponse({'success': False, 'message': 'This item has already been cancelled.'}, status=400)

        with transaction.atomic():
            # ── Stock restore ──────────────────────────────────────────────
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            # ── Proportional refund calculation ────────────────────────────
            # Use the sum of all non-cancelled/returned items' subtotals
            # (including the current item) as the base for coupon proportion.
            original_active_subtotal = order.items.filter(
                is_cancelled=False, is_returned=False
            ).aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')

            if original_active_subtotal > 0 and order.coupon_discount > 0:
                # What fraction of the basket does this item represent?
                item_proportion = item.subtotal / original_active_subtotal
                item_coupon_share = (item_proportion * order.coupon_discount).quantize(Decimal('0.01'))
            else:
                item_coupon_share = Decimal('0.00')

            # item.subtotal already reflects product/brand offer price
            item_refund_base = item.subtotal - item_coupon_share

            # ── Update order totals ────────────────────────────────────────
            order.subtotal -= item.subtotal

            active_items_count = order.items.filter(
                is_cancelled=False, is_returned=False
            ).exclude(id=item.id).count()

            refund_amount = Decimal('0.00')

            if active_items_count == 0:
                # Last item — refund everything remaining and zero out the order
                if order.is_paid or order.payment_status == 'paid':
                    refund_amount = item_refund_base + order.delivery_charge
                order.delivery_charge = Decimal('0.00')
                order.coupon_discount = Decimal('0.00')
                order.total_amount = Decimal('0.00')
            else:
                # Reduce coupon_discount proportionally so future cancellations
                # still calculate correctly against the remaining basket.
                order.coupon_discount -= item_coupon_share
                order.total_amount = order.subtotal + order.delivery_charge - order.coupon_discount
                if order.is_paid or order.payment_status == 'paid':
                    refund_amount = item_refund_base

            # ── Mark item cancelled ────────────────────────────────────────
            item.is_cancelled = True
            item.cancelled_at = timezone.now()
            item.item_status = 'cancelled'
            item.save()

            # ── Wallet refund if paid ──────────────────────────────────────
            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet, order=order,
                    amount=refund_amount, transaction_type='credit'
                )

            # ── Cancel whole order if last item ───────────────────────────
            if active_items_count == 0:
                order.order_status = 'cancelled'
                order.cancellation_reason = 'All items cancelled'
                order.cancelled_at = timezone.now()
                if order.is_paid or order.payment_status == 'paid':
                    order.payment_status = 'refunded'
                    order.is_paid = False
                else:
                    order.payment_status = 'failed'
                    order.is_paid = False

            order.save()

        msg = (f'Item cancelled. ₹{refund_amount} refunded to your wallet.'
               if refund_amount > 0 else 'Item cancelled successfully.')
        messages.success(request, msg)

        return JsonResponse({
            'success': True,
            'message': 'Item cancelled successfully',
            'new_subtotal': float(order.subtotal),
            'new_total': float(order.total_amount),
            'refund_amount': float(refund_amount),
            'active_items_count': active_items_count,
            'order_cancelled': active_items_count == 0
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error cancelling item: {str(e)}'}, status=500)

# ─────────────────────────────────────────────
# RETURN ENTIRE ORDER (admin approval required)
# ─────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def request_return(request, order_number):
    """Request return for entire order — NO wallet refund until admin approves."""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)

        if order.order_status != 'delivered':
            return JsonResponse({'success': False, 'message': 'Only delivered orders can be returned.'})

        if hasattr(order, 'return_request'):
            return JsonResponse({'success': False, 'message': 'Return request already exists for this order.'})

        days_since_delivery = (timezone.now() - order.updated_at).days
        if days_since_delivery > 7:
            return JsonResponse({'success': False, 'message': 'Return period has expired (7 days).'})

        data = json.loads(request.body)
        return_reason = data.get('reason')
        description = data.get('description', '')

        if not return_reason:
            return JsonResponse({'success': False, 'message': 'Please select a reason for return.'})

        with transaction.atomic():
            OrderReturn.objects.create(
                order=order,
                return_reason=return_reason,
                description=description[:500],
                refund_amount=order.total_amount,  # full amount customer paid
                return_status='pending'
            )
            order.order_status = 'returned_checking'
            order.save()

        return JsonResponse({
            'success': True,
            'message': 'Return request submitted! Our team is reviewing it.',
            'redirect_url': f'/orders/detail/{order_number}/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error processing return: {str(e)}'})

# ─────────────────────────────────────────────
# RETURN SINGLE ITEM
# ─────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def request_item_return(request, order_number, item_id):
    """
    Return one item — instant stock restore and proportional wallet refund.

    Refund = item.subtotal − item's proportional share of coupon_discount
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)

        if order.order_status != 'delivered':
            return JsonResponse({'success': False, 'message': 'Only delivered orders can have items returned.'})

        item = get_object_or_404(OrderItem, id=item_id, order=order)

        if item.is_cancelled:
            return JsonResponse({'success': False, 'message': 'Cannot return a cancelled item.'})
        if item.is_returned:
            return JsonResponse({'success': False, 'message': 'This item has already been returned.'})
        if hasattr(item, 'return_request'):
            return JsonResponse({'success': False, 'message': 'Return request already exists for this item.'})

        days_since_delivery = (timezone.now() - order.updated_at).days
        if days_since_delivery > 7:
            return JsonResponse({'success': False, 'message': 'Return period has expired (7 days).'})

        data = json.loads(request.body)
        return_reason = data.get('reason')
        description = data.get('description', '')

        if not return_reason:
            return JsonResponse({'success': False, 'message': 'Please select a reason for return.'})

        with transaction.atomic():
            # ── Proportional refund calculation ────────────────────────────
            # Sum active (non-cancelled, non-returned) items including this one
            original_active_subtotal = order.items.filter(is_cancelled=False, is_returned=False).aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')

            if original_active_subtotal > 0 and order.coupon_discount > 0:
                item_proportion = item.subtotal / original_active_subtotal
                item_coupon_share = (item_proportion * order.coupon_discount).quantize(Decimal('0.01'))
            else:
                item_coupon_share = Decimal('0.00')

            # item.subtotal already reflects product/brand offer price
            refund_amount = item.subtotal - item_coupon_share

            # ── Create return record ───────────────────────────────────────
            OrderItemReturn.objects.create(
                order_item=item,
                order=order,
                return_reason=return_reason,
                description=description[:500],
                refund_amount=refund_amount,
                return_status='approved'
            )

            # ── Mark item returned ─────────────────────────────────────────
            item.is_returned = True
            item.returned_at = timezone.now()
            item.save()

            # ── Stock restore ──────────────────────────────────────────────
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            # ── Wallet refund ──────────────────────────────────────────────
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += refund_amount
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet, order=order,
                amount=refund_amount, transaction_type='credit'
            )

            # ── Update order totals ────────────────────────────────────────
            order.subtotal -= item.subtotal
            # Reduce stored coupon_discount so next return calculates correctly
            order.coupon_discount -= item_coupon_share
            order.total_amount = order.subtotal + order.delivery_charge - order.coupon_discount

            active_items_count = order.items.filter(
                is_cancelled=False, is_returned=False
            ).count()

            if active_items_count == 0:
                if not hasattr(order, 'return_request'):
                    OrderReturn.objects.create(
                        order=order,
                        return_reason=return_reason,
                        description=f"Last item returned: {description[:450]}" if description else "All items returned",
                        refund_amount=Decimal('0.00'),
                        return_status='pending'
                    )
                order.order_status = 'returned_checking'

            order.save()

        return JsonResponse({
            'success': True,
            'message': f'Item returned! ₹{refund_amount:.2f} refunded to your wallet.',
            'redirect_url': f'/orders/detail/{order_number}/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error processing return: {str(e)}'})

@login_required
def download_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.filter(item_status='active'),
        'delivery_address': order.delivery_address,
    }
    
    return render(request, "user_side/profile/order_pdf.html", context)


@login_required
def generate_pdf(request, order_number):
    """Generate and download PDF invoice"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'delivery_address': order.delivery_address,
    }
    
    html_string = render_to_string('user_side/profile/invoice_template.html', context)
    html = HTML(string=html_string)
    result = html.write_pdf()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order_number}.pdf"'
    response.write(result)
    
    return response

    
# Admin
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminOrderListView(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    orders = Order.objects.select_related('user', 'address').prefetch_related('items').all()
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    total_revenue = Order.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    completed_orders = Order.objects.filter(order_status='delivered').count()
    
    pending_payment_amount = Order.objects.filter(
        payment_status='pending'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    pending_payment_count = Order.objects.filter(payment_status='pending').count()
    
    payment_stats = Order.objects.values('payment_status').annotate(
        count=Count('id')
    )
    
    paid_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'paid'), 0)
    pending_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'pending'), 0)
    failed_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'failed'), 0)
    
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 10) 
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    filter_status_choices = [
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('returned_checking', 'Return Checking'),
    ]
    
    context = {
        'orders': page_obj,
        'total_revenue': total_revenue,
        'completed_orders': completed_orders,
        'pending_payment_amount': pending_payment_amount,
        'pending_payment_count': pending_payment_count,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'failed_count': failed_count,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': filter_status_choices,
    }
    
    return render(request, "admin_panel/order_management/order_management.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminOrderUpdateStatusView(request, order_id):
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            new_status = request.POST.get('status')
            current_status = order.order_status
            
            if current_status == 'cancelled':
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot modify cancelled orders.'
                }, status=400)
            
            if new_status == 'cancelled':
                return JsonResponse({
                    'success': False,
                    'message': 'Admins cannot cancel orders.'
                }, status=400)

            if current_status == 'delivered':
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot modify delivered orders.'
                }, status=400)
            
            if current_status in ['returned', 'returned_checking']:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot modify orders with return status.'
                }, status=400)

            valid_transitions = {
                'confirmed': ['shipped'],
                'shipped': ['out_for_delivery'],
                'out_for_delivery': ['delivered'],
            }

            if current_status not in valid_transitions:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot update order from {current_status} status.'
                }, status=400)
            
            if new_status not in valid_transitions[current_status]:
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid status transition from {current_status} to {new_status}.'
                }, status=400)

            order.order_status = new_status
            payment_updated = False

            if new_status == 'delivered':
                order.payment_status = 'paid'
                order.is_paid = True
                payment_updated = True

            order.save(update_fields=['order_status', 'payment_status', 'is_paid', 'updated_at'])

            return JsonResponse({
                'success': True,
                'message': f'Order status updated to {new_status.replace("_", " ").title()}',
                'new_status': new_status,
                'payment_updated': payment_updated  
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminHandleReturnView(request, order_id):
    """Handle approve/reject return requests"""
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            action = request.POST.get('action')
            
            if order.order_status != 'returned_checking':
                return JsonResponse({
                    'success': False,
                    'message': 'This order is not pending return approval.'
                }, status=400)
            try:
                return_request = order.return_request
            except OrderReturn.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'No return request found for this order.'
                }, status=400)
            
            if action == 'approved':
                try:
                    with transaction.atomic():
                        return_request.return_status = 'approved'
                        return_request.processed_at = timezone.now()
                        return_request.save()
                        
                        order.order_status = 'returned'
                        order.payment_status = 'refunded'
                        order.save(update_fields=['order_status', 'payment_status', 'updated_at'])
                        
                        from products.models import ProductVariant
                        for order_item in order.items.all():
                            if order_item.variant:  
                                ProductVariant.objects.filter(id=order_item.variant.id).update(
                                    stock=F('stock') + order_item.quantity
                                )

                        wallet, created = Wallet.objects.get_or_create(user=order.user)

                        refund_amount = return_request.refund_amount

                        wallet.balance += refund_amount
                        wallet.save()

                        transaction_data = {
                            'wallet': wallet,
                            'transaction_type': 'credit',
                            'amount': refund_amount,
                            'order': order,
                        }
                        
                        try:
                            WalletTransaction.objects.create(
                                **transaction_data,
                                description=f'Refund for returned order {order.order_number}'
                            )
                        except TypeError:
                            WalletTransaction.objects.create(**transaction_data)
                        
                        return JsonResponse({
                            'success': True,
                            'message': f'Return approved. ₹{refund_amount} refunded to customer wallet and stock restored.'
                        })
                        
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"Return approval error: {error_details}") 
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed to process return approval: {str(e)}'
                    }, status=500)
                    
            elif action == 'rejected':
                return_request.return_status = 'rejected'
                return_request.processed_at = timezone.now()
                return_request.save()

                order.order_status = 'delivered'
                order.save(update_fields=['order_status', 'updated_at'])
                
                return JsonResponse({
                    'success': True,
                    'message': 'Return request rejected. Order status restored to Delivered.'
                })
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action. Must be "approved" or "rejected".'
                }, status=400)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Return handling error: {error_details}") 
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminOrderDetailView(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return_request = None
    try:
        return_request = order.return_request
    except OrderReturn.DoesNotExist:
        pass
    
    context = {
        'order': order,
        'return_request': return_request
    }
    
    return render(request, 'admin_panel/order_management/order_detail.html', context)