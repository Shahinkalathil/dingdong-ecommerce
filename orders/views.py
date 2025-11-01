from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Order, OrderItem
from datetime import datetime, timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import Order, OrderItem
from products.models import ProductVariant
import json

@login_required
def order(request):
    """Display user's orders with filtering and pagination"""
    # Get all orders with related data
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items__variant__images',
        'items__variant__product',
        'delivery_address'
    ).select_related('user', 'address')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    # Date range filter
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
    
    # Pagination - 5 orders per page
    paginator = Paginator(orders, 4)
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
    
    # Calculate discount
    discount = 0
    if hasattr(order, 'discount_amount'):
        discount = order.discount_amount
    
    # Calculate order savings (discount shown in HTML)
    order_savings = discount
    
    # Check if order can be cancelled (only if pending or confirmed)
    can_cancel = order.order_status in ['pending', 'confirmed']
    
    # Check if order can be returned (only if delivered and within return window)
    can_return = order.order_status == 'delivered'
    
    # Check if invoice can be downloaded (only if delivered)
    can_download_invoice = order.order_status == 'delivered'
    
    # Determine order status steps
    status_steps = {
        'confirmed': order.order_status in ['confirmed', 'processing', 'shipped', 'delivered'],
        'shipped': order.order_status in ['shipped', 'delivered'],
        'out_for_delivery': order.order_status == 'delivered',
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
    }
    
    return render(request, 'user_side/profile/order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel entire order and restore product quantities"""
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__variant'),
            order_number=order_number,
            user=request.user
        )
        
        # Check if order can be cancelled
        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'message': 'Order cannot be cancelled at this stage.'
            }, status=400)
        
        # Get cancellation reason
        data = json.loads(request.body)
        cancel_reason = data.get('reason', '')
        
        with transaction.atomic():
            # Restore quantities for all items
            for item in order.items.all():
                if item.variant:
                    item.variant.stock_quantity += item.quantity
                    item.variant.save()
            
            # Update order status
            order.order_status = 'cancelled'
            order.save()
            
            # Store cancellation reason if needed
            # You might want to add a cancel_reason field to Order model
        
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
    """Cancel individual order item and restore product quantity"""
    try:
        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user
        )
        
        # Check if order can be modified
        if order.order_status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'message': 'Order items cannot be cancelled at this stage.'
            }, status=400)
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        
        with transaction.atomic():
            # Restore product quantity
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()
            
            # Update order totals
            order.subtotal -= item.subtotal
            
            # Recalculate total (subtotal - discount + delivery + tax)
            # Assuming you have these fields, adjust as needed
            discount = getattr(order, 'discount_amount', 0)
            tax = getattr(order, 'tax_amount', 0)
            order.total_amount = order.subtotal - discount + order.delivery_charge + tax
            
            # Delete the item
            item.delete()
            
            # If no items left, cancel the entire order
            if order.items.count() == 0:
                order.order_status = 'cancelled'
            
            order.save()
        
        messages.success(request, 'Item cancelled successfully.')
        return JsonResponse({
            'success': True,
            'message': 'Item cancelled successfully',
            'new_subtotal': float(order.subtotal),
            'new_total': float(order.total_amount),
            'items_count': order.items.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error cancelling item: {str(e)}'
        }, status=500)


@login_required
@require_POST
def request_return(request, order_number):
    """Request return for delivered order"""
    try:
        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user
        )
        
        # Check if order is delivered
        if order.order_status != 'delivered':
            return JsonResponse({
                'success': False,
                'message': 'Only delivered orders can be returned.'
            }, status=400)
        
        # Get return details
        data = json.loads(request.body)
        return_reason = data.get('reason', '')
        return_description = data.get('description', '')
        
        if not return_reason or not return_description:
            return JsonResponse({
                'success': False,
                'message': 'Please provide return reason and description.'
            }, status=400)
        
        # Here you would typically:
        # 1. Create a Return/ReturnRequest model entry
        # 2. Update order status or add a flag
        # 3. Send notification to admin
        
        # For now, we'll just update the order status
        # You might want to create a separate Return model
        order.order_status = 'return_requested'
        order.save()
        
        messages.success(request, 'Return request submitted successfully.')
        return JsonResponse({
            'success': True,
            'message': 'Return request submitted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error requesting return: {str(e)}'
        }, status=500)


@login_required
def download_invoice(request, order_number):
    """Download invoice for delivered order"""
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__variant__product'
        ).select_related('delivery_address', 'user'),
        order_number=order_number,
        user=request.user
    )
    
    # Check if order is delivered
    if order.order_status != 'delivered':
        messages.error(request, 'Invoice is only available for delivered orders.')
        return redirect('order_detail', order_number=order_number)
    
    # Here you would generate PDF invoice
    # For now, returning a simple response
    # You can use libraries like ReportLab or WeasyPrint for PDF generation
    
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_number}.pdf"'
    
    # Add PDF generation logic here
    # For demonstration, returning placeholder
    response.write(b'Invoice PDF content would go here')
    
    return response