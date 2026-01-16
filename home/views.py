from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control
from products.models import Product, ProductVariant, Category, Brand
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Banner
from django.core.paginator import Paginator
from django.db.models import Min, Count, Q
import random
from decimal import Decimal

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def HomeView(request):
    if not request.user.is_authenticated:
        return redirect('sign_in')
    
    banners = Banner.get_active_banners()
    all_categories = list(Category.objects.filter(
        is_listed=True,
        products__is_listed=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_listed=True))
    ).filter(product_count__gt=0).select_related())
    featured_categories = random.sample(all_categories, min(5, len(all_categories))) if all_categories else []
    all_brands = list(Brand.objects.filter(
        is_listed=True,
        products__is_listed=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_listed=True))
    ).filter(product_count__gt=0).select_related())
    brands = random.sample(all_brands, min(8, len(all_brands))) if all_brands else []
    featured_products = Product.objects.filter(
        is_listed=True,
        category__is_listed=True,
        brand__is_listed=True,
        variants__is_listed=True,
        variants__stock__gt=0
    ).annotate(
        min_price=Min('variants__price')
    ).distinct().order_by('id')
    products_data = []
    for product in featured_products:
        default_variant = product.variants.filter(
            is_listed=True,
            stock__gt=0
        ).first()
        
        if default_variant:
            available_variants = product.variants.filter(
                is_listed=True,
                stock__gt=0
            ).values('id', 'color_name', 'color_code')
            
            image = default_variant.images.first()
            products_data.append({
                'product': product,
                'variant': default_variant,
                'image': image,
                'price': default_variant.price,
                'in_stock': default_variant.stock > 0,
                'available_variants': list(available_variants)
            })
    paginator = Paginator(products_data, 8)
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    context = { 
        'banners': banners,
        'categories': featured_categories,
        'brands': brands,
        'products_data': products_page,
        'has_banners': len(banners) > 0,
    }
    
    return render(request, 'user_side/index.html', context)

def RepairServiceView(request):
    return render(request, 'user_side/about/Repair_and_Service.html')

def brands(request):
    brands = Brand.objects.filter(is_listed=True).order_by('name')
    
    context = {
        'brands': brands,
    }
    return render(request, 'user_side/brands/brands.html', context)

def categories(request):
    categories = Category.objects.filter(is_listed=True).order_by('name')
    context = {
        'categories': categories,
    }
    return render(request, 'user_side/brands/category.html', context)

