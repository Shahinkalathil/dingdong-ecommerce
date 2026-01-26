from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.contrib import messages
from django.db.models import Q
from products.models import Brand
from offers.models import BrandOffer
from django.utils import timezone


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


# Add new brand
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandCreateView(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        image = request.FILES.get('image')
        is_listed = request.POST.get('is_listed') == 'on'
        
        # Validation
        if not name:
            messages.error(request, 'Brand name is required.')
            return redirect('add_brand')
        
        # Check if brand already exists
        if Brand.objects.filter(name__iexact=name).exists():
            messages.error(request, 'A brand with this name already exists.')
            return redirect('add_brand')
        
        # Create brand
        try:
            brand = Brand.objects.create(
                name=name,
                image=image,
                is_listed=is_listed
            )
            messages.success(request, f'Brand "{brand.name}" added successfully!')
            return redirect('admin_brands')
        except Exception as e:
            messages.error(request, f'Error adding brand: {str(e)}')
            return redirect('add_brand')
    
    return render(request, 'admin_panel/brands/add_brand.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
def AdminBrandUpdateView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    # Get existing brand offer if any
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
    except BrandOffer.DoesNotExist:
        brand_offer = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle brand update
        if action == 'update_brand':
            name = request.POST.get('name', '').strip()
            is_listed = request.POST.get('is_listed') == 'on'
            remove_image = request.POST.get('remove_image') == 'on'
            image = request.FILES.get('image')
            
            # Validation
            if not name:
                messages.error(request, 'Brand name is required.')
                return redirect('edit_brand', brand_id=brand_id)
            
            # Check if another brand with same name exists
            if Brand.objects.filter(name__iexact=name).exclude(id=brand_id).exists():
                messages.error(request, 'A brand with this name already exists.')
                return redirect('edit_brand', brand_id=brand_id)
            
            try:
                brand.name = name
                brand.is_listed = is_listed
                
                # Handle image logic
                if image:
                    # New image uploaded - replace old one
                    if brand.image:
                        brand.image.delete(save=False)
                    brand.image = image
                elif remove_image and brand.image:
                    # Remove image without replacement
                    brand.image.delete(save=False)
                    brand.image = None
                
                brand.save()
                messages.success(request, f'Brand "{brand.name}" updated successfully!')
                return redirect('edit_brand', brand_id=brand_id)
            except Exception as e:
                messages.error(request, f'Error updating brand: {str(e)}')
                return redirect('edit_brand', brand_id=brand_id)
              
    context = {
        'brand': brand,
        'brand_offer': brand_offer,
    }
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



       

