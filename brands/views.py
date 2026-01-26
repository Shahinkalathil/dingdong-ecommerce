from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.contrib import messages
from django.db.models import Q
from products.models import Brand
from offers.models import BrandOffer
from django.utils import timezone
from django.core.files.images import get_image_dimensions


# Create your views here.

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandListView(request):
    brands = Brand.objects.all().order_by('-id')
    context = {
        'brands': brands,
        'keyword': None
    }
    return render(request, 'admin_panel/brands/brand_management.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandToggleListView(request, brand_id):
    """
    Returns brand detail modal HTML content (not a full page)
    """
    brand = get_object_or_404(Brand, id=brand_id)
    
    # Try to get the brand offer if it exists
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
    except BrandOffer.DoesNotExist:
        brand_offer = None
    
    context = {
        'brand': brand,
        'brand_offer': brand_offer,
        'now': timezone.now(),
    }
    
    # Return only the modal HTML content (not a full page)
    return render(request, 'admin_panel/brands/brand_detail_modal.html', context)

# Search brands
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandsearchView(request):
    keyword = request.GET.get('keyword', '').strip()
    
    if keyword:
        brands = Brand.objects.filter(
            Q(name__icontains=keyword)
        ).order_by('-id')
    else:
        brands = Brand.objects.all().order_by('-id')
    
    context = {
        'brands': brands,
        'keyword': keyword
    }
    return render(request, 'admin_panel/brands/brand_management.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandCreateView(request):
    context = {
        'errors': {},
        'old_name': '',
    }
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        image = request.FILES.get("image")

        errors = {}

        # Brand Name Validation
        if not name:
            errors['name'] = "Brand name is required."
        elif len(name) > 50:
            errors['name'] = "Brand name must be 50 characters or less."
        elif Brand.objects.filter(name__iexact=name).exists():
            errors['name'] = "A brand with this name already exists."

        # Image Validation 
        if image:
            try:
                if not image.content_type.startswith('image/'):
                    errors['image'] = "File must be an image (JPG, PNG, WEBP)."
                if image.size > 2 * 1024 * 1024:
                    errors['image'] = "Image file size must be less than 2MB."
                width, height = get_image_dimensions(image)
                if width > 2000 or height > 2000:
                    errors['image'] = "Image dimensions too large (max 2000x2000)."
            except Exception:
                errors['image'] = "Invalid image file."

        # re-render with old data & errors
        if errors:
            context = {
                'errors': errors,
                'old_name': name,
            }
            return render(request, "admin_panel/brands/add_brand.html", context)

        Brand.objects.create(
            name=name,
            image=image
        )
        return redirect('admin_brands')
    return render(request, "admin_panel/brands/add_brand.html", context)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandUpdateView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    # Get existing brand offer if any
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
    except BrandOffer.DoesNotExist:
        brand_offer = None
    
    # Prepare context
    context = {
        'brand': brand,
        'brand_offer': brand_offer,
        'errors': {},  # ← Field-specific errors will go here
        'old_name': brand.name,  # For repopulating on error
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle brand update
        if action == 'update_brand':
            name = request.POST.get('name', '').strip()
            is_listed = request.POST.get('is_listed') == 'on'
            remove_image = request.POST.get('remove_image') == 'on'
            image = request.FILES.get('image')
            
            errors = {}

            # 1. Brand Name Validation
            if not name:
                errors['name'] = "Brand name is required."
            elif len(name) > 50:
                errors['name'] = "Brand name must be 50 characters or less."
            elif Brand.objects.filter(name__iexact=name).exclude(id=brand_id).exists():
                errors['name'] = "A brand with this name already exists."

            # 2. Image Validation (if new image uploaded)
            if image:
                try:
                    if not image.content_type.startswith('image/'):
                        errors['image'] = "File must be an image (JPG, PNG, WEBP)."
                    if image.size > 2 * 1024 * 1024:
                        errors['image'] = "Image file size must be less than 2MB."
                    width, height = get_image_dimensions(image)
                    if width > 2000 or height > 2000:
                        errors['image'] = "Image dimensions too large (max 2000x2000)."
                except Exception:
                    errors['image'] = "Invalid image file."

            # If there are errors → re-render form with old values & errors
            if errors:
                context['errors'] = errors
                context['old_name'] = name
                return render(request, 'admin_panel/brands/edit_brand.html', context)

            # No errors → update brand
            try:
                brand.name = name
                brand.is_listed = is_listed
                
                # Handle image logic
                if image:
                    # New image uploaded - replace old one
                    if brand.image:
                        brand.image.delete(save=False)
                    brand.image = image
                    brand.is_listed = True
                elif remove_image and brand.image:
                    # Remove image without replacement
                    brand.image.delete(save=False)
                    brand.image = None
                
                brand.save()
                return redirect('edit_brand', brand_id=brand_id)
            except Exception as e:
                return render(request, 'admin_panel/brands/edit_brand.html', context)

    return render(request, 'admin_panel/brands/edit_brand.html', context)

# Toggle brand status (List/Unlist)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandStatusView(request, brand_id):
    if request.method == 'POST':
        brand = get_object_or_404(Brand, id=brand_id)
        brand.is_listed = not brand.is_listed
        brand.save()
        
        status = "listed" if brand.is_listed else "unlisted"
        messages.success(request, f'Brand "{brand.name}" has been {status}.')
    
    return redirect('admin_brands')



       

