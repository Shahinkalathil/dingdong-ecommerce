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
from django.db.models import Min,  Q, Max
import random
from decimal import Decimal
import base64
import io
from offers.models import ProductOffer
from offers.utils import get_best_offer_price

# User Side
# -------------------------------------------

def products(request):
    products=Product.objects.filter(is_listed=True,category__is_listed=True,brand__is_listed=True,variants__is_listed=True
    ).prefetch_related("variants__images","variants"
    ).select_related("brand","category").distinct()

    categories=Category.objects.filter(is_listed=True)
    brands=Brand.objects.filter(is_listed=True)

    search_query=request.GET.get('search','').strip()
    if search_query:
        products=products.filter(Q(name__icontains=search_query)|
        Q(description__icontains=search_query)|
        Q(brand__name__icontains=search_query)|
        Q(category__name__icontains=search_query))

    category_filter=request.GET.get('category','').strip()
    if category_filter:
        products=products.filter(category__id=category_filter)

    brand_filter=request.GET.get('brand','').strip()
    if brand_filter:
        products=products.filter(brand__id=brand_filter)

    price_range=request.GET.get('price_range','').strip()
    if price_range=='0-1000':
        products=products.filter(variants__price__range=(0,1000))
    elif price_range=='1000-3000':
        products=products.filter(variants__price__range=(1000,3000))
    elif price_range=='3000-5000':
        products=products.filter(variants__price__range=(3000,5000))
    elif price_range=='5000-10000':
        products=products.filter(variants__price__range=(5000,10000))
    elif price_range=='10000+':
        products=products.filter(variants__price__gte=10000)

    sort_by=request.GET.get('sort','').strip()
    if sort_by=='price-low':
        products=products.annotate(min_price=Min('variants__price')).order_by('min_price')
    elif sort_by=='price-high':
        products=products.annotate(max_price=Max('variants__price')).order_by('-max_price')
    elif sort_by=='name-az':
        products=products.order_by('name')
    elif sort_by=='name-za':
        products=products.order_by('-name')
    else:
        products=products.order_by('-id')

    paginator=Paginator(products.distinct(),15)
    page_obj=paginator.get_page(request.GET.get('page'))

    product_display_data=[]
    for product in page_obj:
        variants=product.variants.filter(is_listed=True)
        lowest_variant=variants.order_by('price').first()
        if not lowest_variant:
            continue
        total_stock=sum(v.stock for v in variants)
        original_price=lowest_variant.price
        final_price,discount_percentage=get_best_offer_price(product,original_price)
        product_display_data.append(
            {
                'product':product,
                'variant':lowest_variant,
                'first_image':lowest_variant.images.first(),
                'original_price':original_price,
                'final_price':final_price,
                'discount_percentage':discount_percentage,
                'in_stock':total_stock>0,
                'total_stock':total_stock,
                'rating':round(random.uniform(3.5,5.0),1),
                'review_count':random.randint(10,500)
                })
    context={
        'page_obj':page_obj,
        'product_display_data':product_display_data,
        'categories':categories,
        'brands':brands,
        'search_query':search_query,
        'selected_category':category_filter,
        'selected_brand':brand_filter,
        'selected_price_range':price_range,
        'selected_sort':sort_by,
        'total_products':paginator.count
        }
    return render(request,'user_side/product/product_listing.html', context)

# Product Detail
def product_detail(request, variant_id):
    """
    Product detail view that handles variant selection via URL parameter
    """
    try:
        # Get the variant directly from the URL
        default_variant = get_object_or_404(ProductVariant, id=variant_id, is_listed=True)
        product = default_variant.product
        
        # Check if product, category, and brand are listed
        if not product.is_listed or not product.category.is_listed or not product.brand.is_listed:
            messages.error(request, "This product is not available.")
            return redirect('products')
        
        # Get all listed variants for this product
        variants = ProductVariant.objects.filter(
            product=product, 
            is_listed=True
        ).prefetch_related('images')
        
        if not variants.exists():
            messages.error(request, "No variants available for this product.")
            return redirect('products')
        
        # Get wishlist variant IDs for authenticated users
        wishlist_variants = []
        is_in_wishlist = False
        is_in_cart = False
        
        if request.user.is_authenticated:
            wishlist_variants = list(WishlistItem.objects.filter(
                user=request.user
            ).values_list("variant_id", flat=True))
            is_in_wishlist = default_variant.id in wishlist_variants
            
            # Check if variant is in cart
            try:
                from cart.models import Cart, CartItem
                user_cart = Cart.objects.get(user=request.user)
                is_in_cart = CartItem.objects.filter(cart=user_cart, variant=default_variant).exists()
            except Cart.DoesNotExist:
                is_in_cart = False
        
        # Calculate pricing with offers
        original_price = default_variant.price
        final_price, discount_percentage = get_best_offer_price(product, original_price)
        
        # Determine which offer is being applied
        offer_type = None
        offer_name = None
        
        product_offer = getattr(product, "product_offer", None)
        brand_offer = getattr(product.brand, "brand_offer", None)
        
        if product_offer and product_offer.is_valid() and product_offer.discount_percentage == discount_percentage:
            offer_type = "Product Offer"
            offer_name = f"{discount_percentage}% off on this product"
        elif brand_offer and brand_offer.is_active and brand_offer.discount_percentage == discount_percentage:
            offer_type = "Brand Offer"
            offer_name = f"{discount_percentage}% off on all {product.brand.name} products"
        
        # Calculate total stock across all variants
        total_stock = sum(variant.stock for variant in variants)
        
        # Get related products (same category, different product)
        related_products = Product.objects.filter(
            category=product.category,
            is_listed=True
        ).exclude(id=product.id).prefetch_related('variants__images')[:4]
        
        related_products_data = []
        for related_product in related_products:
            related_variant = related_product.variants.filter(is_listed=True).first()
            if related_variant:
                rel_original_price = related_variant.price
                rel_final_price, rel_discount = get_best_offer_price(related_product, rel_original_price)
                
                related_products_data.append({
                    'product': related_product,
                    'variant': related_variant,
                    'original_price': rel_original_price,
                    'final_price': rel_final_price,
                    'discount_percentage': rel_discount,
                    'rating': round(random.uniform(3.5, 5.0), 1),
                    'review_count': random.randint(20, 1000),
                })
        
        # Specifications
        specifications = {
            'Brand': product.brand.name,
            'Category': product.category.name,
            'Material': 'Premium Quality',
            'Warranty': '2 Years',
            'Color Options': ', '.join([v.color_name for v in variants]),
            'Current Color': default_variant.color_name,
        }
        
        # Prepare variants data for template
        variants_data = []
        for variant in variants:
            variant_price, variant_discount = get_best_offer_price(product, variant.price)
            variants_data.append({
                'id': variant.id,
                'color_name': variant.color_name,
                'color_code': variant.color_code,
                'stock': variant.stock,
                'original_price': variant.price,
                'final_price': variant_price,
                'discount_percentage': variant_discount,
                'images': list(variant.images.all()),
                'is_current': variant.id == default_variant.id,
            })
        
        # Mock ratings and reviews
        rating = round(random.uniform(3.5, 5.0), 1)
        review_count = random.randint(50, 5000)
        
        context = {
            'product': product,
            'variants': variants,
            'variants_data': variants_data,
            'default_variant': default_variant,
            'wishlist_variants': wishlist_variants,
            'is_in_wishlist': is_in_wishlist,
            'is_in_cart': is_in_cart,
            'rating': rating,
            'review_count': review_count,
            'original_price': original_price,
            'final_price': final_price,
            'discount_percentage': discount_percentage,
            'offer_type': offer_type,
            'offer_name': offer_name,
            'current_variant_stock': default_variant.stock,
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
                    'name': f'Customer {random.randint(1, 100)}',
                    'rating': random.randint(4, 5),
                    'comment': 'Great product! Highly recommend.',
                    'verified': True
                },
                {
                    'name': f'Customer {random.randint(1, 100)}',
                    'rating': random.randint(3, 5),
                    'comment': 'Good value for money. Fast delivery.',
                    'verified': True
                }
            ]
        }
        
        return render(request, "user_side/product/product_detail.html", context)
        
    except ProductVariant.DoesNotExist:
        messages.error(request, "Product variant not found.")
        return redirect('products')
    except Exception as e:
        print(f"Error in product_detail: {e}")
        messages.error(request, "An error occurred while loading the product.")
        return redirect('products')

# Adminside
# -------------------------------------------
# product management
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminProductListView(request):
    products = Product.objects.select_related("product_offer").prefetch_related("variants__images")

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
    """
    Combined view to handle:
    1. Product and existing variant updates
    2. New variant creation
    """
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.prefetch_related("images").all()
    
    try:
        product_offer = ProductOffer.objects.get(product=product)
    except ProductOffer.DoesNotExist:
        product_offer = None
    
    context = {
        'product_offer': product_offer, 
        'errors': {},  
        'old_name': product.name, 
        "product": product,
        "brands": Brand.objects.filter(is_listed=True),
        "categories": Category.objects.filter(is_listed=True),
        "variants": variants, 
    }
    
    if request.method == "GET":
        return render(request,"admin_panel/product/product_edit.html", context)
    
    if request.method == "POST":
        form_type = request.POST.get('form_type')
        
        # ---- Handle NEW VARIANT CREATION ----
        if form_type == 'add_variant':
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
                messages.error(request, "Please fix the errors in the new variant form.")
                context['variant_errors'] = variant_errors
                context['form_data'] = form_data
                return render(request, "admin_panel/product/product_edit.html", context)
            
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
            
            messages.success(request, f"Successfully added {variants_created} new variant(s)!")
            return redirect("edit_products", product_id=product.id)
        
        # ---- Handle EXISTING PRODUCT/VARIANT UPDATE ----
        elif form_type == 'update_product':
            # ---- Check if list/unlist action ----
            for index, variant in enumerate(variants, start=1):
                action_field = f"variant_action_{index}"
                if action_field in request.POST:
                    action = request.POST.get(action_field)
                    if action == "list":
                        variant.is_listed = True
                        messages.success(request, f"Variant '{variant.color_name}' has been listed.")
                    elif action == "unlist":
                        variant.is_listed = False
                        messages.success(request, f"Variant '{variant.color_name}' has been unlisted.")
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
            
            messages.success(request, "Product and variants updated successfully!")
            return redirect("edit_products", product_id=product.id)
    
    return render(request, "admin_panel/product/product_edit.html", context)


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


