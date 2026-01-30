from datetime import datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from products.models import Brand
from .models import BrandOffer, ProductOffer
from django.views.decorators.http import require_POST
from products.models import Product, Category, Brand
from decimal import Decimal, InvalidOperation



def AdminBrandOfferCreateView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand_offer = BrandOffer.objects.filter(brand=brand).first()
    discount = request.POST.get('discount_percentage', '').strip()
    valid_until = request.POST.get('valid_until', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        valid_until_date = timezone.make_aware(
            datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
        )

        if brand_offer:
            brand_offer.discount_percentage = discount
            brand_offer.valid_until = valid_until_date
            brand_offer.is_active = is_active
            brand_offer.updated_at = timezone.now()
            brand_offer.save()
        else:
            BrandOffer.objects.create(
                brand=brand,
                discount_percentage=discount,
                valid_until=valid_until_date,
                is_active=is_active
            ) 
    except Exception as e:
        pass
    return redirect('edit_brand', brand_id=brand_id)

@require_POST  
def AdminBrandOfferDeleteView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
        brand_offer.delete()
    except BrandOffer.DoesNotExist:
        pass
    return redirect('edit_brand', brand_id=brand_id)

@require_POST  
def AdminBrandBlockView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
        brand_offer.is_active = not brand_offer.is_active
        brand_offer.save()  
    except BrandOffer.DoesNotExist:
        pass
    return redirect('edit_brand', brand_id=brand_id)


@require_POST
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductOfferCreateView(request, product_id):
    """
    Handle creating or updating product offers
    """
    product = get_object_or_404(Product, id=product_id)
    product_offer = ProductOffer.objects.filter(product=product).first()

    discount = request.POST.get('discount_percentage', '').strip()
    valid_until = request.POST.get('valid_until', '').strip()
    
    errors = {}
    
    # Validate discount percentage
    try:
        discount_decimal = Decimal(discount)
        if discount_decimal <= 0:
            errors['discount_percentage'] = "Discount must be greater than 0."
        elif discount_decimal > 100:
            errors['discount_percentage'] = "Discount cannot exceed 100%."
    except (ValueError, InvalidOperation):
        errors['discount_percentage'] = "Please enter a valid discount percentage."
    
    # Validate valid_until date
    try:
        valid_until_date = timezone.make_aware(
            datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
        )
        
        # Check if date is in the past
        if valid_until_date <= timezone.now():
            errors['valid_until'] = "Expiry date must be in the future."
            
    except (ValueError, TypeError):
        errors['valid_until'] = "Please enter a valid date and time."
    
    # If there are errors, return to the edit page with error context
    if errors:
        variants = product.variants.prefetch_related("images").all()
        context = {
            'product_offer': product_offer,
            'errors': errors,
            'old_name': product.name,
            'product': product,
            'brands': Brand.objects.filter(is_listed=True),
            'categories': Category.objects.filter(is_listed=True),
            'variants': variants,
        }
        return render(request, 'admin_panel/product/product_edit.html', context)
    
    # No errors - proceed with save
    try:
        if product_offer:
            # Update existing offer
            product_offer.discount_percentage = discount_decimal
            product_offer.valid_until = valid_until_date
            product_offer.save()
            messages.success(request, "Product offer updated successfully!")
        else:
            # Create new offer
            ProductOffer.objects.create(
                product=product,
                discount_percentage=discount_decimal,
                valid_until=valid_until_date,
                is_active=True
            )
            messages.success(request, "Product offer created successfully!")
    except Exception as e:
        messages.error(request, f"Error saving offer: {str(e)}")
    
    return redirect('edit_products', product_id=product.id)


@require_POST
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductOfferToggleView(request, product_id):
    """
    Toggle product offer active/inactive status
    """
    product = get_object_or_404(Product, id=product_id)
    product_offer = get_object_or_404(ProductOffer, product=product)
    
    # Toggle the active status
    product_offer.is_active = not product_offer.is_active
    product_offer.save()
    
    status = "activated" if product_offer.is_active else "deactivated"
    messages.success(request, f"Product offer {status} successfully!")
    
    return redirect('edit_products', product_id=product.id)


@require_POST
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductOfferDeleteView(request, product_id):
    """
    Delete product offer
    """
    product = get_object_or_404(Product, id=product_id)
    product_offer = get_object_or_404(ProductOffer, product=product)
    
    try:
        product_offer.delete()
        messages.success(request, "Product offer deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting offer: {str(e)}")
    
    return redirect('edit_products', product_id=product.id)
