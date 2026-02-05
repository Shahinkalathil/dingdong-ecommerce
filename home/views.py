
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_control
from products.models import Product, Category, Brand
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Banner
from django.core.paginator import Paginator
from django.db.models import Min, Count, Q
from offers.utils import get_best_offer_price



@cache_control(no_cache=True, no_store=True, must_revalidate=True)  # prevent caching after logout
def HomeView(request):
    if not request.user.is_authenticated:  # protect home page
        return redirect('sign_in')

    banners = Banner.get_active_banners()  # only active banners

    categories = list(
        Category.objects.filter(is_listed=True, products__is_listed=True)
        .annotate(product_count=Count('products', filter=Q(products__is_listed=True)))  # count visible products
        .filter(product_count__gt=0)  # hide empty categories
        .distinct()
    )

    brands = list(
        Brand.objects.filter(is_listed=True, products__is_listed=True)
        .annotate(product_count=Count('products', filter=Q(products__is_listed=True)))  # count visible products
        .filter(product_count__gt=0)  # hide empty brands
        .distinct()
    )

    featured_products = Product.objects.filter(
        is_listed=True,
        category__is_listed=True,
        brand__is_listed=True,
        variants__is_listed=True,
        variants__stock__gt=0  # ensure sellable products only
    ).annotate(
        min_price=Min('variants__price')  # used for price display/sorting
    ).distinct().order_by('id')

    products_data = []

    for product in featured_products:
        default_variant = product.variants.filter(
            is_listed=True,
            stock__gt=0
        ).first()  # default selectable variant

        if not default_variant:
            continue  # safety check

        available_variants = product.variants.filter(
            is_listed=True,
            stock__gt=0
        ).values('id', 'color_name', 'color_code')  # for color swatches

        image = default_variant.images.first()  # thumbnail image

        final_price, discount_percentage = get_best_offer_price(
            product,
            default_variant.price  # apply product/brand/category offers
        )

        products_data.append({
            'id': default_variant.id,  # required for wishlist
            'product': product,
            'variant': default_variant,
            'image': image,
            'price': round(final_price, 2),
            'original_price': default_variant.price,
            'final_price': round(final_price, 2),
            'discount_percentage': round(discount_percentage, 1),
            'in_stock': default_variant.stock > 0,
            'available_variants': list(available_variants)
        })

    paginator = Paginator(products_data, 8)  # homepage grid limit
    page = request.GET.get('page', 1)

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    return render(request, 'user_side/index.html', {
        'banners': banners,
        'categories': categories,
        'brands': brands,
        'products_data': products_page,
        'has_banners': bool(banners)  # template helper
    })


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
