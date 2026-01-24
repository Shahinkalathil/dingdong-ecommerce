from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from .models import Coupon 
from datetime import datetime

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminCouponsListView(request):
    """Display list of all coupons"""
    # Fetch all coupons ordered by creation date
    coupons = Coupon.objects.all().order_by('-created_at')
    view_coupon_id = request.GET.get('view_coupon')
    selected_coupon = None
    if view_coupon_id:
        try:
            selected_coupon = Coupon.objects.get(id=view_coupon_id)
        except Coupon.DoesNotExist:
            messages.error(request, "Coupon not found")
    
    context = {
        'coupons': coupons,
        'now': timezone.now(),
        'selected_coupon': selected_coupon,
    }
    return render(request, 'admin_panel/coupons/coupon_management.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminCouponsSearchView(request):
    """Search coupons by code or filter by active/inactive status"""
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    coupons = Coupon.objects.all()

    # Filter by search query
    if query:
        coupons = coupons.filter(code__icontains=query)

    # Filter by status
    if status_filter == 'active':
        coupons = coupons.filter(is_active=True)
    elif status_filter == 'inactive':
        coupons = coupons.filter(is_active=False)

    coupons = coupons.order_by('-created_at')

    context = {
        'query': query,
        'coupons': coupons,
        'now': timezone.now(),
        'search_query': query,
        'status_filter': status_filter,
    }
    return render(request, 'admin_panel/coupons/coupon_management.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminCouponsCreateView(request):
    """Create a new coupon - Admin view"""
    if request.method == "POST":
        data = request.POST
        errors = {}

        # Extract and clean data
        code = data.get("couponCode", "").strip().upper()
        discount_str = data.get("discountValue", "").strip()
        min_purchase_str = data.get("minPurchase", "").strip()
        max_discount_str = data.get("maxDiscount", "").strip()
        valid_from_str = data.get("validFrom", "").strip()
        valid_until_str = data.get("validUntil", "").strip()
        usage_limit_str = data.get("usageLimit", "").strip()
        

        # ── Validation ────────────────────────────────────────────────────────

        # Coupon Code
        if not code:
            errors["couponCode"] = "Coupon code is required"
        elif len(code) > 20:
            errors["couponCode"] = "Coupon code must be 20 characters or less"
        elif not code.isalnum():
            errors["couponCode"] = "Coupon code can only contain letters (A-Z) and numbers (0-9)"
        elif not (any(c.isalpha() for c in code) and any(c.isdigit() for c in code)):
            # ← NEW: Must contain at least one letter AND one number
            errors["couponCode"] = "Coupon code must contain both letters and numbers"
        elif Coupon.objects.filter(code=code).exists():
            errors["couponCode"] = "This coupon code already exists"
        # Discount Percentage
        discount = None
        if not discount_str:
            errors["discountValue"] = "Discount percentage is required"
        else:
            try:
                discount = int(discount_str)
                if discount < 1 or discount > 100:
                    errors["discountValue"] = "Discount must be between 1% and 100%"
            except ValueError:
                errors["discountValue"] = "Discount must be a valid number"

        # Minimum Purchase
        min_purchase = None
        if not min_purchase_str:
            errors["minPurchase"] = "Minimum purchase amount is required"
        else:
            try:
                min_purchase = Decimal(min_purchase_str)
                if min_purchase < 0:
                    errors["minPurchase"] = "Minimum purchase cannot be negative"
            except (InvalidOperation, ValueError):
                errors["minPurchase"] = "Minimum purchase must be a valid number"

        # Max Discount (optional)
        max_discount = None
        if max_discount_str:
            try:
                max_discount = Decimal(max_discount_str)
                if max_discount <= 0:
                    errors["maxDiscount"] = "Max discount must be greater than 0"
            except (InvalidOperation, ValueError):
                errors["maxDiscount"] = "Max discount must be a valid number"

        # Dates - Very Important!
        valid_from = None
        valid_until = None

        DATE_FORMAT = "%Y-%m-%d"  

        if not valid_from_str:
            errors["validFrom"] = "Valid from date is required"
        else:
            try:
                valid_from = datetime.strptime(valid_from_str, DATE_FORMAT)
                valid_from = timezone.make_aware(valid_from)  
            except ValueError:
                errors["validFrom"] = "Invalid date format (use YYYY-MM-DD)"

        if not valid_until_str:
            errors["validUntil"] = "Valid until date is required"
        else:
            try:
                valid_until = datetime.strptime(valid_until_str, DATE_FORMAT)
                valid_until = timezone.make_aware(valid_until)
            except ValueError:
                errors["validUntil"] = "Invalid date format (use YYYY-MM-DD)"

        # Additional date logic
        if valid_from and valid_until:
            if valid_until <= valid_from:
                errors["validUntil"] = "Valid until date must be after valid from date"
            if valid_from < timezone.now():
                pass

        # Usage Limits
        usage_limit = None
        if not usage_limit_str:
            errors["usageLimit"] = "Total usage limit is required"
        else:
            try:
                usage_limit = int(usage_limit_str)
                if usage_limit < 1:
                    errors["usageLimit"] = "Usage limit must be at least 1"
            except ValueError:
                errors["usageLimit"] = "Usage limit must be a valid number"

        # If there are errors → return to form
        if errors:
            return render(request, "admin_panel/coupons/coupon_add.html", {
                "errors": errors,
                "old": data,  
            })

        # ── Create Coupon ─────────────────────────────────────────────────────
        try:
            Coupon.objects.create(
                code=code,
                discount_percentage=discount,
                min_purchase_amount=min_purchase,
                max_discount_amount=max_discount,
                valid_from=valid_from,
                valid_until=valid_until,
                usage_limit=usage_limit,
                is_active=True,
            )
            messages.success(request, f"Coupon '{code}' created successfully!")
            return redirect("admin_coupons")  # or whatever your list URL name is
        except Exception as e:
            errors["general"] = f"Error creating coupon: {str(e)}"
            return render(request, "admin_panel/coupons/coupon_add.html", {
                "errors": errors,
                "old": data,
            })

    # GET request → show empty form
    return render(request, "admin_panel/coupons/coupon_add.html")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminCouponsUpdateView(request, coupon_id):
    """Edit an existing coupon"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == "POST":
        data = request.POST
        errors = {}

        code = data.get("couponCode", "").strip().upper()
        discount = data.get("discountValue", "").strip()
        min_purchase = data.get("minPurchase", "").strip()
        max_discount = data.get("maxDiscount", "").strip()
        valid_from = data.get("validFrom", "").strip()
        valid_until = data.get("validUntil", "").strip()
        usage_limit = data.get("usageLimit", "").strip()
        

        # Validation (same as create)
        if not code:
            errors["couponCode"] = "Coupon code is required"
        elif len(code) > 20:
            errors["couponCode"] = "Coupon code must be 20 characters or less"
        elif not code.isalnum():
            errors["couponCode"] = "Coupon code can only contain letters (A-Z) and numbers (0-9)"
        elif not (any(c.isalpha() for c in code) and any(c.isdigit() for c in code)):
            # ← NEW: Must contain at least one letter AND one number
            errors["couponCode"] = "Coupon code must contain both letters and numbers"
        elif Coupon.objects.filter(code=code).exists():
            errors["couponCode"] = "This coupon code already exists"

        if not discount:
            errors["discountValue"] = "Discount percentage is required"
        else:
            try:
                discount = int(discount)
                if discount < 1 or discount > 100:
                    errors["discountValue"] = "Discount must be between 1% and 100%"
            except ValueError:
                errors["discountValue"] = "Discount must be a valid number"

        if not min_purchase:
            errors["minPurchase"] = "Minimum purchase amount is required"
        else:
            try:
                min_purchase = Decimal(min_purchase)
                if min_purchase < 0:
                    errors["minPurchase"] = "Minimum purchase cannot be negative"
            except:
                errors["minPurchase"] = "Minimum purchase must be a valid number"

        if max_discount:
            try:
                max_discount = Decimal(max_discount)
                if max_discount <= 0:
                    errors["maxDiscount"] = "Max discount must be greater than 0"
            except:
                errors["maxDiscount"] = "Max discount must be a valid number"
        else:
            max_discount = None

        if not valid_from:
            errors["validFrom"] = "Valid from date is required"

        if not valid_until:
            errors["validUntil"] = "Valid until date is required"

        if valid_from and valid_until and not errors.get("validFrom") and not errors.get("validUntil"):
            try:
                valid_from_dt = timezone.datetime.strptime(valid_from, "%Y-%m-%d")
                valid_until_dt = timezone.datetime.strptime(valid_until, "%Y-%m-%d")
                
                valid_from_dt = timezone.make_aware(valid_from_dt)
                valid_until_dt = timezone.make_aware(valid_until_dt)
                
                if valid_until_dt <= valid_from_dt:
                    errors["validUntil"] = "Expiry date must be after start date"
            except:
                errors["general"] = "Invalid date format"

        if not usage_limit:
            errors["usageLimit"] = "Total usage limit is required"
        else:
            try:
                usage_limit = int(usage_limit)
                if usage_limit < 1:
                    errors["usageLimit"] = "Usage limit must be at least 1"
            except ValueError:
                errors["usageLimit"] = "Usage limit must be a valid number"

        if errors:
            return render(request, "admin_panel/coupons/coupon_edit.html", {
                "errors": errors,
                "coupon": coupon,
                "old": data
            })

        try:
            coupon.code = code
            coupon.discount_percentage = discount
            coupon.min_purchase_amount = min_purchase
            coupon.max_discount_amount = max_discount
            coupon.valid_from = valid_from_dt
            coupon.valid_until = valid_until_dt
            coupon.usage_limit = usage_limit
            coupon.save()
            
            messages.success(request, "Coupon updated successfully!")
            return redirect("admin_coupons")
        except Exception as e:
            errors["general"] = f"Error updating coupon: {str(e)}"
            return render(request, "admin_panel/coupons/coupon_edit.html", {
                "errors": errors,
                "coupon": coupon,
                "old": data
            })

    context = {'coupon': coupon}
    return render(request, "admin_panel/coupons/coupon_edit.html", context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminCouponsToggleStatusView(request, coupon_id):
    """
    Toggle coupon active/inactive status
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == "POST":
        try:
            coupon.is_active = not coupon.is_active
            coupon.save()
            status = "activated" if coupon.is_active else "deactivated"
            messages.success(request, f"Coupon '{coupon.code}' {status} successfully!")
        except Exception as e:
            messages.error(request, f"Error updating coupon status: {str(e)}")
    
    return redirect("admin_coupons")