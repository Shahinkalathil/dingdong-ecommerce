from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.core.files.base import ContentFile
from django.contrib import messages
from PIL import Image
from wishlist.models import WishlistItem
from .models import Category, Product, Brand, ProductVariant, ProductImage
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Min,  Q
import random
from decimal import Decimal
import base64
import io
from django.db import transaction
import uuid

# Userside
# -------------------------------------------
# Product Listing
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

# Product Detail
def product_detail(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)

        if not product.is_listed or not product.category.is_listed or not product.brand.is_listed:
            return redirect('products')

        variants = ProductVariant.objects.filter(product=product, is_listed=True).prefetch_related('images')
        if not variants.exists():
            return redirect('products')
            
        variant_id = request.GET.get("variant")
        if variant_id:
            try:
                default_variant = variants.get(id=variant_id)
            except ProductVariant.DoesNotExist:
                default_variant = variants.first()
        else:
            default_variant = variants.first()

        # Get wishlist variants for current user
        wishlist_variants = []
        if request.user.is_authenticated:
            wishlist_variants = WishlistItem.objects.filter(
                user=request.user
            ).values_list("variant_id", flat=True)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
        rating = round(random.uniform(3.5, 5.0), 1)
        review_count = random.randint(50, 5000)
        original_price = default_variant.price * Decimal('1.2')
        discount_percentage = round(((original_price - default_variant.price) / original_price) * 100)
        current_variant_stock = default_variant.stock
        total_stock = sum(variant.stock for variant in variants)
        related_products = Product.objects.filter(category=product.category,is_listed=True).exclude(id=product.id).prefetch_related('variants__images')[:4]

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

        specifications = {
            'Brand': product.brand.name,
            'Category': product.category.name,
            'Material': 'Premium Quality',
            'Warranty': '2 Years',
            'Color Options': ', '.join([v.color_name for v in variants]),
            'Current Color': default_variant.color_name,
        }

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
            "wishlist_variants": wishlist_variants,
            'product': product,
            'variants': variants,
            'variants_data': variants_data,  
            'default_variant': default_variant,
            'rating': rating,
            'review_count': review_count,
            'original_price': original_price,
            'discount_percentage': discount_percentage,
            'current_variant_stock': current_variant_stock,  
            'total_stock': total_stock,  
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
        print(e)
        return redirect('products')



# Adminside
# -------------------------------------------
# product management
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductListView(request):
    products = Product.objects.prefetch_related("variants__images").all()
    context = {
        "products": products,
    }
    return render(request, 'admin_panel/product/product_management.html', context) # product page

# Product Detail
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductDetailView(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.prefetch_related("images").filter(is_listed=True)
    context ={
        "product": product,
        "variants": variants
    }
    return render(request, "admin_panel/product/product_variant.html", context) #product listing page

# Product Search
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductsearchView(request):
    keyword = request.GET.get('keyword', "").strip()
    print("Keyword:", keyword)
    product = Product.objects.all()

    if keyword:
        products = product.filter(
            Q(name__icontains =  keyword) |
            Q(category__name__icontains = keyword) |
            Q(brand__name__icontains = keyword)
        )
    context = {
        "products": products,
        "keyword": keyword,
    }
    return render(request, "admin_panel/product/product_management.html", context) #search

# Product Create
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductCreateView(request):
    categories = Category.objects.filter(is_listed=True)
    brands = Brand.objects.filter(is_listed=True)
    
    if request.method == "POST":
        product_name = request.POST.get("product_name", "").strip()
        product_description = request.POST.get("product_description", "").strip()
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        errors = {}
        form_data = request.POST.copy()

        if not product_name:
            errors["product_name"] = "Product name is required."
        elif Product.objects.filter(name__iexact=product_name).exists():
            errors["product_name"] = f"A product with the name '{product_name}' already exists."
        if not product_description:
            errors["product_description"] = "Product description is required."
        if not category_id:
            errors["category"] = "Please select a category."
        if not brand_id:
            errors["brand"] = "Please select a brand."

        variant_prices = request.POST.getlist('variant_price[]')
        variant_stocks = request.POST.getlist('variant_stock[]')
        variant_color_names = request.POST.getlist('variant_color_name[]')
        variant_color_hexs = request.POST.getlist('variant_color_hex[]')
        
        cropped_images = {}
        for i in range(len(variant_prices)):
            cropped_images[i] = {}
            for img_num in range(1, 5):
                field_name = f'variant_image_{img_num}_cropped[]'
                cropped_data_list = request.POST.getlist(field_name)
                if i < len(cropped_data_list) and cropped_data_list[i]:
                    cropped_images[i][img_num] = cropped_data_list[i]

        variant_errors = []
        for i in range(len(variant_prices)):
            ve = {}

            try:
                price = float(variant_prices[i])
                if price < 0:
                    ve["price"] = "Price must be a positive number."
            except (ValueError, IndexError):
                ve["price"] = "Price must be a number."

            try:
                stock = int(variant_stocks[i])
                if stock < 0:
                    ve["stock"] = "Stock must be a positive integer."
            except (ValueError, IndexError):
                ve["stock"] = "Stock must be an integer."

            try:
                if not variant_color_names[i].strip():
                    ve["color_name"] = "Color name is required."
            except IndexError:
                ve["color_name"] = "Color name is required."

            cropped_image_count = 0
            if i in cropped_images:
                for img_num in range(1, 5):
                    if img_num in cropped_images[i] and cropped_images[i][img_num]:
                        cropped_image_count += 1
            
            if cropped_image_count != 4:
                ve["images"] = "Exactly 4 cropped images must be provided for this variant."
            
            variant_errors.append(ve)

        if errors or any(variant_errors):
            return render(request, "admin_panel/product/product_add.html", {
                "errors": errors,
                "variant_errors": variant_errors,
                "form_data": form_data,
                "categories": categories,
                "brands": brands
            })
        
        category = Category.objects.get(id=category_id)
        brand = Brand.objects.get(id=brand_id)
        product = Product.objects.create(
            name=product_name,
            description=product_description,
            category=category,
            brand=brand,
            is_listed=True
        )
        
        for i in range(len(variant_prices)):
            variant = ProductVariant.objects.create(
                product=product,
                price=float(variant_prices[i]),
                stock=int(variant_stocks[i]),
                color_name=variant_color_names[i],
                color_code=variant_color_hexs[i],
            )

            if i in cropped_images:
                for img_num in range(1, 5):
                    if img_num in cropped_images[i] and cropped_images[i][img_num]:
                        try:
                            image_file = process_base64_image(
                                cropped_images[i][img_num],
                                f"{product_name}_variant_{i+1}_img_{img_num}"
                            )
                            
                            if image_file:
                                ProductImage.objects.create(
                                    variant=variant,
                                    image=image_file
                                )
                        except Exception as e:
                            print(f"Error processing cropped image: {e}")

        return redirect("admin_products")
    
    context = {
        "categories": categories,
        "brands": brands,
    }
    return render(request, 'admin_panel/product/product_add.html', context)

def process_base64_image(base64_data, filename):
    """
    Process base64 image data and return a Django file object
    """
    try:
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        image_data = base64.b64decode(base64_data)

        image = Image.open(io.BytesIO(image_data))

        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        output = io.BytesIO()
        image.save(output, format='JPEG', quality=90, optimize=True)
        output.seek(0)

        django_file = ContentFile(
            output.getvalue(),
            name=f"{filename}.jpg"
        )
        
        return django_file
        
    except Exception as e:
        print(f"Error processing base64 image: {e}")
        return None

# Product Update
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductUpdateView(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.prefetch_related("images").all()
    if request.method == "GET":
        return render(
            request,
            "admin_panel/product/product_edit.html",
            {
                "product": product,
                "brands": Brand.objects.filter(is_listed=True),
                "categories": Category.objects.filter(is_listed=True),
                "variants": variants,
            }
        )
    if request.method == "POST":
        # ---- Check if list/unlist action ----
        for index, variant in enumerate(variants, start=1):
            action_field = f"variant_action_{index}"
            if action_field in request.POST:
                action = request.POST.get(action_field)
                if action == "list":
                    variant.is_listed = True
                elif action == "unlist":
                    variant.is_listed = False
                variant.save()
                return redirect("edit_products", product_id=product.id)
        # ---- Product update ----
        product.name = request.POST.get("product_name", "").strip()
        product.description = request.POST.get("product_description", "").strip()
        brand_id = request.POST.get("product_brand")
        category_id = request.POST.get("product_category")
        if brand_id:
            product.brand = Brand.objects.get(id=brand_id)

        if category_id:
            product.category = Category.objects.get(id=category_id)
        product.save()

        # ---- Variants update ----
        for index, variant in enumerate(variants, start=1):
            color_name = request.POST.get(f"color_name_{index}")
            color_code = request.POST.get(f"color_code_{index}")
            price = request.POST.get(f"price_{index}")
            stock = request.POST.get(f"stock_{index}")
            if not color_name:
                continue
            variant.color_name = color_name
            variant.color_code = color_code or "#000000"
            variant.price = price or variant.price
            variant.stock = stock or variant.stock
            variant.save()

            # ---- Replace images ----
            for img_slot in range(1, 5):  
                field_name = f"image{img_slot}_{index}"
                image_file = request.FILES.get(field_name)

                if image_file:
                    existing_images = variant.images.all().order_by('id')
                    if img_slot <= existing_images.count():
                        old_image = existing_images[img_slot - 1]
                        old_image.image = image_file
                        old_image.save()
                    else:
                        ProductImage.objects.create(
                            variant=variant,
                            image=image_file
                        )
        return redirect("edit_products", product_id=product.id)

# Product Delecte
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductVariantDeleteView(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product
    current_variant_count = product.variants.count()
    if current_variant_count <= 1:
        messages.error(request,"Cannot delete the last variant of a product.")
        return redirect("edit_products", product_id=product.id)
    variant_color = variant.color_name
    variant.delete()
    messages.success(request,f"Variant '{variant_color}' was successfully deleted.")
    return redirect("edit_products", product_id=product.id)


# Add Variant to Existing Product
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductVariantAddView(request, product_id):
    """
    Add new variants to an existing product
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return redirect("admin_products")
    
    if request.method == "POST":
        variant_prices = request.POST.getlist('variant_price[]')
        variant_stocks = request.POST.getlist('variant_stock[]')
        variant_color_names = request.POST.getlist('variant_color_name[]')
        variant_color_hexs = request.POST.getlist('variant_color_hex[]')
        
        # Collect cropped images
        cropped_images = {}
        for i in range(len(variant_prices)):
            cropped_images[i] = {}
            for img_num in range(1, 5):
                field_name = f'variant_image_{img_num}_cropped[]'
                cropped_data_list = request.POST.getlist(field_name)
                if i < len(cropped_data_list) and cropped_data_list[i]:
                    cropped_images[i][img_num] = cropped_data_list[i]

        # Validation
        errors = {}
        variant_errors = []
        
        for i in range(len(variant_prices)):
            ve = {}

            # Validate price
            try:
                price = float(variant_prices[i])
                if price < 0:
                    ve["price"] = "Price must be a positive number."
            except (ValueError, IndexError):
                ve["price"] = "Price must be a number."

            # Validate stock
            try:
                stock = int(variant_stocks[i])
                if stock < 0:
                    ve["stock"] = "Stock must be a positive integer."
            except (ValueError, IndexError):
                ve["stock"] = "Stock must be an integer."

            # Validate color name
            try:
                if not variant_color_names[i].strip():
                    ve["color_name"] = "Color name is required."
            except IndexError:
                ve["color_name"] = "Color name is required."

            # Validate images (exactly 4 required)
            cropped_image_count = 0
            if i in cropped_images:
                for img_num in range(1, 5):
                    if img_num in cropped_images[i] and cropped_images[i][img_num]:
                        cropped_image_count += 1
            
            if cropped_image_count != 4:
                ve["images"] = "Exactly 4 cropped images must be provided for this variant."
            
            variant_errors.append(ve)

        # If there are errors, return to form with errors
        if any(variant_errors):
            form_data = request.POST.copy()
            return render(request, "admin_panel/product/product_edit.html", {
                "errors": errors,
                "variant_errors": variant_errors,
                "form_data": form_data,
                "product": product
            })
        
        # Create variants
        variants_created = 0
        for i in range(len(variant_prices)):
            variant = ProductVariant.objects.create(
                product=product,
                price=float(variant_prices[i]),
                stock=int(variant_stocks[i]),
                color_name=variant_color_names[i],
                color_code=variant_color_hexs[i],
            )

            # Process and save images
            if i in cropped_images:
                for img_num in range(1, 5):
                    if img_num in cropped_images[i] and cropped_images[i][img_num]:
                        try:
                            image_file = process_base64_image(
                                cropped_images[i][img_num],
                                f"{product.name}_variant_{variant.id}_img_{img_num}"
                            )
                            
                            if image_file:
                                ProductImage.objects.create(
                                    variant=variant,
                                    image=image_file
                                )
                        except Exception as e:
                            print(f"Error processing cropped image: {e}")
            
            variants_created += 1
        
        return redirect("edit_products", product_id=product_id)
    
    # GET request - show form
    context = {
        "product": product,
    }
    return render(request, 'admin_panel/product/product_variant_add.html', context)


