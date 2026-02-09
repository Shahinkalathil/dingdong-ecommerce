from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from wallet.models import WalletTransaction
from orders.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()


# Userside
# -------------------------------------------
# Wallet Listing
def wallet_view(request):
    return render(request, 'user_side/profile/wallet/wallet.html')



# Admin Side
# -------------------------------------------
# Admin Wallet Management View

@login_required
def AdminPaymentListView(request):
    """Admin view to list all payments (Orders + Wallet Transactions)"""
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)
    
    # Get all orders
    orders = Order.objects.select_related('user').all()
    
    # Search functionality
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(razorpay_payment_id__icontains=search_query) |
            Q(payment_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    orders = orders.order_by('-created_at')
    
    # Get wallet transactions
    wallet_transactions = WalletTransaction.objects.select_related('wallet__user', 'order').all()
    
    if search_query:
        wallet_transactions = wallet_transactions.filter(
            Q(wallet__user__username__icontains=search_query) |
            Q(wallet__user__email__icontains=search_query) |
            Q(order__order_number__icontains=search_query)
        )
    
    wallet_transactions = wallet_transactions.order_by('-created_at')
    
    # Combine payments
    payments = []
    
    # Add orders to payments list
    for order in orders:
        payments.append({
            'type': 'order',
            'transaction_id': f"PAY-{order.created_at.year}-{str(order.id).zfill(6)}",
            'order_id': order.order_number,
            'customer': order.user.username,
            'customer_email': order.user.email,
            'date': order.created_at,
            'amount': order.total_amount,
            'payment_method': order.get_payment_method_display(),
            'payment_method_code': order.payment_method,
            'status': order.payment_status,
            'order_obj': order,
        })
    
    # Add wallet transactions to payments list
    for transaction in wallet_transactions:
        payments.append({
            'type': 'wallet',
            'transaction_id': f"WAL-{transaction.created_at.year}-{str(transaction.id).zfill(6)}",
            'order_id': transaction.order.order_number if transaction.order else '-',
            'customer': transaction.wallet.user.username,
            'customer_email': transaction.wallet.user.email,
            'date': transaction.created_at,
            'amount': transaction.amount,
            'payment_method': 'Wallet',
            'payment_method_code': 'wallet',
            'status': 'paid',
            'transaction_type': transaction.transaction_type,
            'wallet_transaction': transaction,
        })
    
    # Sort by date
    payments.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate statistics
    total_payments = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    paid_amount = Order.objects.filter(payment_status='paid').aggregate(
        total=Sum('total_amount'))['total'] or 0
    pending_amount = Order.objects.filter(payment_status='pending').aggregate(
        total=Sum('total_amount'))['total'] or 0
    refunded_amount = Order.objects.filter(payment_status='refunded').aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Pagination
    paginator = Paginator(payments, 10)
    payments_page = paginator.get_page(page_number)
    
    context = {
        'payments': payments_page,
        'search_query': search_query,
        'total_payments': total_payments,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'refunded_amount': refunded_amount,
        'page_obj': payments_page,
    }
    
    return render(request, 'admin_panel/payment/payment_management.html', context)


@login_required
def AdminPaymentDetailView(request, payment_type, payment_id):
    """Admin view to see detailed payment information"""
    
    if payment_type == 'order':
        # Get order payment details
        order = get_object_or_404(Order.objects.select_related('user', 'address'), id=payment_id)
        
        context = {
            'payment_type': 'order',
            'order': order,
            'items': order.items.all(),
            'transaction_id': f"PAY-{order.created_at.year}-{str(order.id).zfill(6)}",
        }
        
        return render(request, 'admin_panel/payment/payment_detail.html', context)
    
    elif payment_type == 'wallet':
        # Get wallet transaction details
        transaction = get_object_or_404(
            WalletTransaction.objects.select_related('wallet__user', 'order'), 
            id=payment_id
        )
        
        context = {
            'payment_type': 'wallet',
            'transaction': transaction,
            'wallet': transaction.wallet,
            'transaction_id': f"WAL-{transaction.created_at.year}-{str(transaction.id).zfill(6)}",
        }
        
        return render(request, 'admin_panel/payment/payment_detail.html', context)