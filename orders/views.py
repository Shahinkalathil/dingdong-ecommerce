from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Order, OrderItem, OrderReturn
from datetime import datetime, timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST, require_http_methods
import json
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile


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
            for item in order.items.all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
                
                item.is_cancelled = True
                item.cancelled_at = timezone.now()
                item.save()
            
            order.order_status = 'cancelled'
            order.cancellation_reason = cancel_reason
            order.cancelled_at = timezone.now()

            if order.is_paid or order.payment_status == 'paid':
               
                order.payment_status = 'refunded'
                order.is_paid = False
            else:
               
                order.payment_status = 'failed'
                order.is_paid = False
            
            order.save()
        
        messages.success(request, f'Order {order_number} has been cancelled successfully.')
        
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
            'redirect_url': '/orders/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error cancelling order: {str(e)}'
        }, status=500)


@login_required
@require_POST
def cancel_order_item(request, order_number, item_id):
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
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            item.is_cancelled = True
            item.cancelled_at = timezone.now()
            item.save()
    
            order.subtotal -= item.subtotal
            order.total_amount = order.subtotal + order.delivery_charge
            
       
            active_items_count = order.items.filter(is_cancelled=False).count()
            
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
        
        messages.success(request, 'Item cancelled successfully.')
        
        return JsonResponse({
            'success': True,
            'message': 'Item cancelled successfully',
            'new_subtotal': float(order.subtotal),
            'new_total': float(order.total_amount),
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
        
    
        order_return = OrderReturn.objects.create(
            order=order,
            return_reason=return_reason,
            description=description[:500],  
            refund_amount=order.total_amount
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Return request submitted successfully!',
            'redirect_url': f'/orders/{order_number}/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing return request: {str(e)}'
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