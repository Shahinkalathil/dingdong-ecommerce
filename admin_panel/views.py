from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.urls import reverse
from userlogin.models import CustomUser
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from orders.models import Order, OrderItem

# Admin Login
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_index')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect("admin_index")
            else:
                messages.error(request, "You don't have access to the Admin Panel.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "admin_panel/admin_login.html")


# Admin Logout
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def admin_logout(request):
    request.session.flush()
    return redirect("admin_login")


# List Users
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def users(request):
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user
    
    users = CustomUser.objects.exclude(is_superuser=True).order_by("-created_at")
    paginator = Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_users = paginator.get_page(page)

    context = {
        "users": page_users,
        "superusers": superusers,
        "current_super": current_super,
        "is_search": False,
        "keyword": "",
    }
    return render(request, "admin_panel/user_list/users_management.html", context)


# Change User status Block / Unblock
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def user_status(request, id):
    try:
        user = CustomUser.objects.get(id=id)
        if not user.is_superuser:  
            user.is_active = not user.is_active
            user.save()
            
            action = "unblocked" if user.is_active else "blocked"
            messages.success(request, f"User {user.fullname} has been {action} successfully.")
        else:
            messages.error(request, "Cannot modify superuser status.")
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")

    keyword = request.GET.get("keyword", "").strip()
    page = request.GET.get("page", 1)

    if keyword:
        return redirect(f"{reverse('users_search')}?keyword={keyword}&page={page}")
    else:
        return redirect(f"{reverse('admin_users')}?page={page}")


# Search Users
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def users_search(request):
    keyword = request.GET.get("keyword", "").strip()
    message = None
    users = CustomUser.objects.none() 

    if keyword:
        users = CustomUser.objects.filter(
            Q(id__icontains=keyword) |
            Q(fullname__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(phone__icontains=keyword) |
            Q(created_at__date__icontains=keyword)
        ).exclude(is_superuser=True).order_by("-created_at")

        if not users.exists():
            message = f"No users found matching '{keyword}'"
    else:
        return redirect('admin_users')

    paginator = Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_users = paginator.get_page(page)

    context = {
        "users": page_users,
        "message": message,
        "keyword": keyword,
        "is_search": True,
        "total_results": users.count() if keyword else 0,
    }
    return render(request, "admin_panel/user_list/users_management.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def admin_order(request):
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    orders = Order.objects.select_related('user', 'address').prefetch_related('items').all()
    
    # Apply search filter
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    # Calculate statistics
    total_revenue = Order.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    completed_orders = Order.objects.filter(order_status='delivered').count()
    
    pending_payment_amount = Order.objects.filter(
        payment_status='pending'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    pending_payment_count = Order.objects.filter(payment_status='pending').count()
    
    # Payment status counts
    payment_stats = Order.objects.values('payment_status').annotate(
        count=Count('id')
    )
    
    paid_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'paid'), 0)
    pending_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'pending'), 0)
    failed_count = next((item['count'] for item in payment_stats if item['payment_status'] == 'failed'), 0)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Status choices for filter dropdown
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
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            new_status = request.POST.get('status')
            
            # Validation logic
            current_status = order.order_status
            
            # Admin cannot change cancelled orders
            if current_status == 'cancelled':
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot modify cancelled orders.'
                }, status=400)
            
            # Admin cannot set status to cancelled
            if new_status == 'cancelled':
                return JsonResponse({
                    'success': False,
                    'message': 'Admins cannot cancel orders.'
                }, status=400)
            
            # Cannot modify delivered orders
            if current_status == 'delivered':
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot modify delivered orders.'
                }, status=400)
            
            # Define valid status transitions for admin
            valid_transitions = {
                'confirmed': ['shipped'],
                'shipped': ['out_for_delivery'],
                'out_for_delivery': ['delivered'],
            }
            
            # Check if transition is valid
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
            
            # Update the order status
            order.order_status = new_status
            payment_updated = False

            # If order is delivered, automatically set payment status to paid
            if new_status == 'delivered':
                order.payment_status = 'paid'
                order.is_paid = True
                payment_updated = True

            # Save with update_fields to avoid triggering the full save() logic
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
def admin_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_panel/order_management/order_details.html', {'order': order})