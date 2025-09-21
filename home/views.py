from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from products.models import Product, ProductVariant, Category, Brand
from django.core.paginator import Paginator
from django.db.models import Q, Min
import random
from decimal import Decimal


def home(request):
    if request.user.is_authenticated:
        return render(request, 'user_side/index.html')  
    else:
        return redirect('sign_up')  


@login_required
def user_logout(request):
    logout(request)
    return redirect('sign_in')

def products(request):
    products = Product.objects.filter(
        is_listed=True,
        variants__is_listed=True
    ).prefetch_related(
        "variants__images", "brand", "category"
    ).distinct()

    categories = Category.objects.filter(is_listed=True)
    brands = Brand.objects.filter(is_listed=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )

    category_filter = request.GET.get('category', '').strip()
    if category_filter:
        products = products.filter(category__id=category_filter)

    brand_filter = request.GET.get('brand', '').strip()
    if brand_filter:
        products = products.filter(brand__id=brand_filter)

    price_range = request.GET.get('price_range', '').strip()
    if price_range:
        if price_range == '0-1000':
            products = products.filter(variants__price__gte=0, variants__price__lte=1000)
        elif price_range == '1000-3000':
            products = products.filter(variants__price__gte=1000, variants__price__lte=3000)
        elif price_range == '3000-5000':
            products = products.filter(variants__price__gte=3000, variants__price__lte=5000)
        elif price_range == '5000-10000':
            products = products.filter(variants__price__gte=5000, variants__price__lte=10000)
        elif price_range == '10000+':
            products = products.filter(variants__price__gte=10000)

    sort_by = request.GET.get('sort', '').strip()
    if sort_by == 'price-low':
        products = products.annotate(min_price=Min('variants__price')).order_by('min_price')
    elif sort_by == 'price-high':
        products = products.annotate(min_price=Min('variants__price')).order_by('-min_price')
    elif sort_by == 'name-az':
        products = products.order_by('name')
    elif sort_by == 'name-za':
        products = products.order_by('-name')
    else:
        products = products.order_by('-id')  
    products = products.distinct()

    rating = round(random.uniform(3.5, 5.0), 1)
    

    paginator = Paginator(products, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    def get_product_display_data(products_page):
        display_data = []
        for product in products_page:
            first_variant = product.variants.filter(is_listed=True).first()
            if first_variant:
                display_data.append({
                    'product': product,
                    'variant': first_variant,
                    'first_image': first_variant.images.first() if first_variant.images.exists() else None
                })
        return display_data
    
    product_display_data = get_product_display_data(page_obj)
    
    context = {
        'page_obj': page_obj,
        'product_display_data': product_display_data,
        'categories': categories,
        'brands': brands,
        "rating": rating,
        'search_query': search_query,
        'selected_category': category_filter,
        'selected_brand': brand_filter,
        'selected_price_range': price_range,
        'selected_sort': sort_by,
        'total_products': paginator.count,
    }
    
    return render(request, 'user_side/product/product_listing.html', context)

def product_detail(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)

        # Blocked / unlisted product check
        if not product.is_listed or not product.category.is_listed or not product.brand.is_listed:
            return redirect('products')

        variants = ProductVariant.objects.filter(product=product, is_listed=True).prefetch_related('images')
        if not variants.exists():
            return redirect('products')

        # Pick variant from query param if provided
        variant_id = request.GET.get("variant")
        if variant_id:
            try:
                default_variant = variants.get(id=variant_id)
            except ProductVariant.DoesNotExist:
                # If variant doesn't exist, fall back to first variant
                default_variant = variants.first()
        else:
            default_variant = variants.first()

        # AJAX request for variant switching
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON data for AJAX requests
            variant_data = {
                'variant_id': default_variant.id,
                'color_name': default_variant.color_name,
                'color_code': default_variant.color_code,
                'price': str(default_variant.price),
                'stock': default_variant.stock,
                'images': [
                    {
                        'url': image.image.url,
                        'alt': f"{default_variant.color_name} {i+1}"
                    } for i, image in enumerate(default_variant.images.all())
                ] if default_variant.images.exists() else [],
                'original_price': str(default_variant.price * Decimal('1.2')),
                'discount_percentage': round(((default_variant.price * Decimal('1.2') - default_variant.price) / (default_variant.price * Decimal('1.2'))) * 100)
            }
            return JsonResponse(variant_data)

        # Fake rating + reviews
        rating = round(random.uniform(3.5, 5.0), 1)
        review_count = random.randint(50, 5000)

        # Price calculation for selected variant
        original_price = default_variant.price * Decimal('1.2')
        discount_percentage = round(((original_price - default_variant.price) / original_price) * 100)

        # Stock for current variant (not total stock)
        current_variant_stock = default_variant.stock
        
        # Total stock across all variants (for reference)
        total_stock = sum(variant.stock for variant in variants)

        # Related products
        related_products = Product.objects.filter(
            category=product.category,
            is_listed=True
        ).exclude(id=product.id).prefetch_related('variants__images')[:4]

        related_products_data = []
        for related_product in related_products:
            related_variant = related_product.variants.filter(is_listed=True).first()
            if related_variant:
                related_products_data.append({
                    'product': related_product,
                    'variant': related_variant,
                    'rating': round(random.uniform(3.5, 5.0), 1),
                    'review_count': random.randint(20, 1000),
                })

        # Specs
        specifications = {
            'Brand': product.brand.name,
            'Category': product.category.name,
            'Material': 'Premium Quality',
            'Warranty': '2 Years',
            'Color Options': ', '.join([v.color_name for v in variants]),
            'Current Color': default_variant.color_name,
        }

        # Create variants data for template (with stock info)
        variants_data = []
        for variant in variants:
            variants_data.append({
                'id': variant.id,
                'color_name': variant.color_name,
                'color_code': variant.color_code,
                'stock': variant.stock,
                'price': variant.price,
                'images_count': variant.images.count(),
            })

        context = {
            'product': product,
            'variants': variants,
            'variants_data': variants_data,  # Additional data for JavaScript
            'default_variant': default_variant,
            'rating': rating,
            'review_count': review_count,
            'original_price': original_price,
            'discount_percentage': discount_percentage,
            'current_variant_stock': current_variant_stock,  # Current variant stock
            'total_stock': total_stock,  # All variants stock
            'related_products': related_products_data,
            'specifications': specifications,
            'key_features': [
                'Premium build quality',
                'Durable construction',
                'Comfortable design',
                'Long-lasting performance',
                'Modern aesthetics'
            ],
            'reviews': [
                {
                    'name': 'Customer ' + str(random.randint(1, 100)),
                    'rating': random.randint(4, 5),
                    'comment': 'Great product! Highly recommend.',
                    'verified': True
                },
                {
                    'name': 'Customer ' + str(random.randint(1, 100)),
                    'rating': random.randint(3, 5),
                    'comment': 'Good value for money. Fast delivery.',
                    'verified': True
                }
            ]
        }

        return render(request, "user_side/product/product_detail.html", context)
    except Product.DoesNotExist:
        return render(request, "errors/404.html", status=404)
    except Exception as e:
        return redirect('products')