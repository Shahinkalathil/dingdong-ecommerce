from datetime import datetime, timedelta
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST, require_http_methods
from decimal import Decimal

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


@login_required
def order_detail(request, order_number):
    """Display detailed order information"""
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__variant__images',
            'items__variant__product'
        ).select_related('delivery_address', 'user'),
        order_number=order_number,
        user=request.user
    )
    
    discount = 0
    if hasattr(order, 'discount_amount'):
        discount = order.discount_amount
    
    order_savings = discount
    
    can_cancel = order.order_status in ['pending', 'confirmed']
    
    can_download_invoice = order.order_status == 'delivered'
    
    can_return = False
    return_days_left = 0
    
    if order.order_status == 'delivered':
        delivery_date = order.updated_at  
        days_since_delivery = (timezone.now() - delivery_date).days
        return_days_left = 7 - days_since_delivery
        
        if return_days_left > 0 and not hasattr(order, 'return_request'):
            can_return = True

    status_steps = {
        'confirmed': order.order_status in ['confirmed', 'shipped', 'out_for_delivery', 'delivered'],
        'shipped': order.order_status in ['shipped', 'out_for_delivery', 'delivered'],
        'out_for_delivery': order.order_status in ['out_for_delivery', 'delivered'],
        'delivered': order.order_status == 'delivered',
    }
    
    context = {
        'order': order,
        'can_cancel': can_cancel,
        'can_return': can_return,
        'can_download_invoice': can_download_invoice,
        'status_steps': status_steps,
        'discount': discount,
        'order_savings': order_savings,
        'return_days_left': return_days_left if return_days_left > 0 else 0,
    }
    
    return render(request, 'user_side/profile/order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel entire order and refund to wallet"""
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__variant'),
            order_number=order_number,
            user=request.user
        )

        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'message': 'Order cannot be cancelled at this stage.'
            }, status=400)

        data = json.loads(request.body)
        cancel_reason = data.get('reason', 'No reason provided')
        
        with transaction.atomic():
            # Restore stock for all items
            for item in order.items.all():
                if item.variant and not item.is_cancelled:
                    item.variant.stock += item.quantity
                    item.variant.save()
                
                item.is_cancelled = True
                item.cancelled_at = timezone.now()
                item.item_status = 'cancelled'
                item.save()
            
            # Update order status
            order.order_status = 'cancelled'
            order.cancellation_reason = cancel_reason
            order.cancelled_at = timezone.now()

            # Handle refund if order was paid
            refund_amount = Decimal('0.00')
            if order.is_paid or order.payment_status == 'paid':
                refund_amount = order.total_amount
                order.payment_status = 'refunded'
                order.is_paid = False
                
                # Add refund to wallet
                wallet, created = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += refund_amount
                wallet.save()
                
                # Create wallet transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    amount=refund_amount,
                    transaction_type='credit'
                )
            else:
                order.payment_status = 'failed'
                order.is_paid = False
            
            order.save()
        
        if refund_amount > 0:
            messages.success(request, f'Order {order_number} has been cancelled and ₹{refund_amount} has been refunded to your wallet.')
        else:
            messages.success(request, f'Order {order_number} has been cancelled successfully.')
        
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
            'refund_amount': float(refund_amount),
            'redirect_url': '/orders/list/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error cancelling order: {str(e)}'
        }, status=500)


@login_required
@require_POST
def cancel_order_item(request, order_number, item_id):
    """Cancel individual order item and refund proportionate amount"""
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__variant'),
            order_number=order_number,
            user=request.user
        )

        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'message': 'Order items cannot be cancelled at this stage.'
            }, status=400)
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)

        if item.is_cancelled:
            return JsonResponse({
                'success': False,
                'message': 'This item has already been cancelled.'
            }, status=400)
        
        with transaction.atomic():
            # Restore stock
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            # Mark item as cancelled
            item.is_cancelled = True
            item.cancelled_at = timezone.now()
            item.item_status = 'cancelled'
            item.save()
    
            # Recalculate order totals
            order.subtotal -= item.subtotal
            order.total_amount = order.subtotal + order.delivery_charge - order.coupon_discount
            
            # Check if all items are cancelled
            active_items_count = order.items.filter(is_cancelled=False, is_returned=False).count()
            
            # Handle refund for cancelled item
            refund_amount = Decimal('0.00')
            if order.is_paid or order.payment_status == 'paid':
                refund_amount = item.subtotal
                
                # Add refund to wallet
                wallet, created = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += refund_amount
                wallet.save()
                
                # Create wallet transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    amount=refund_amount,
                    transaction_type='credit'
                )
            
            # If all items cancelled, cancel the entire order
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
        
        if refund_amount > 0:
            messages.success(request, f'Item cancelled successfully. ₹{refund_amount} has been refunded to your wallet.')
        else:
            messages.success(request, 'Item cancelled successfully.')
        
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
        return JsonResponse({
            'success': False,
            'message': f'Error cancelling item: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def request_return(request, order_number):
    """Request return for entire order"""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        if order.order_status != 'delivered':
            return JsonResponse({
                'success': False,
                'message': 'Only delivered orders can be returned.'
            })

        if hasattr(order, 'return_request'):
            return JsonResponse({
                'success': False,
                'message': 'Return request already exists for this order.'
            })
 
        delivery_date = order.updated_at  
        days_since_delivery = (timezone.now() - delivery_date).days
        
        if days_since_delivery > 7:
            return JsonResponse({
                'success': False,
                'message': 'Return period has expired. Returns are only valid within 7 days of delivery.'
            })
        
        data = json.loads(request.body)
        return_reason = data.get('reason')
        description = data.get('description', '')
        
        if not return_reason:
            return JsonResponse({
                'success': False,
                'message': 'Please select a reason for return.'
            })
        
        with transaction.atomic():
            # Create return request
            order_return = OrderReturn.objects.create(
                order=order,
                return_reason=return_reason,
                description=description[:500],
                refund_amount=order.total_amount,
                return_status='pending'
            )
            
            # Mark all items as returned
            for item in order.items.filter(is_cancelled=False):
                item.is_returned = True
                item.returned_at = timezone.now()
                item.item_status = 'returned'
                item.save()
                
                # Restore stock
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
            
            # Update order status
            order.order_status = 'returned'
            order.save()
            
            # Add refund to wallet
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += order.total_amount
            wallet.save()
            
            # Create wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=order.total_amount,
                transaction_type='credit'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Return request submitted successfully! ₹{order.total_amount} has been refunded to your wallet.',
            'redirect_url': f'/orders/list/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing return request: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def request_item_return(request, order_number, item_id):
    """Request return for individual item"""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        if order.order_status != 'delivered':
            return JsonResponse({
                'success': False,
                'message': 'Only delivered orders can have items returned.'
            })
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        
        if item.is_cancelled:
            return JsonResponse({
                'success': False,
                'message': 'Cannot return a cancelled item.'
            })
        
        if item.is_returned:
            return JsonResponse({
                'success': False,
                'message': 'This item has already been returned.'
            })
        
        if hasattr(item, 'return_request'):
            return JsonResponse({
                'success': False,
                'message': 'Return request already exists for this item.'
            })
        
        delivery_date = order.updated_at
        days_since_delivery = (timezone.now() - delivery_date).days
        
        if days_since_delivery > 7:
            return JsonResponse({
                'success': False,
                'message': 'Return period has expired. Returns are only valid within 7 days of delivery.'
            })
        
        data = json.loads(request.body)
        return_reason = data.get('reason')
        description = data.get('description', '')
        
        if not return_reason:
            return JsonResponse({
                'success': False,
                'message': 'Please select a reason for return.'
            })
        
        with transaction.atomic():
            # Create item return request
            item_return = OrderItemReturn.objects.create(
                order_item=item,
                order=order,
                return_reason=return_reason,
                description=description[:500],
                refund_amount=item.subtotal,
                return_status='pending'
            )
            
            # Mark item as returned
            item.is_returned = True
            item.returned_at = timezone.now()
            item.item_status = 'returned'
            item.save()
            
            # Restore stock
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
            
            # Add refund to wallet
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += item.subtotal
            wallet.save()
            
            # Create wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=item.subtotal,
                transaction_type='credit'
            )
            
            # Recalculate order totals
            order.subtotal -= item.subtotal
            order.total_amount = order.subtotal + order.delivery_charge - order.coupon_discount
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Item return request submitted successfully! ₹{item.subtotal} has been refunded to your wallet.',
            'refund_amount': float(item.subtotal),
            'new_subtotal': float(order.subtotal),
            'new_total': float(order.total_amount)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing item return: {str(e)}'
        })


@login_required
def download_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
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
def AdminOrderDetailView(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_panel/order_management/order_detail.html', {'order': order})