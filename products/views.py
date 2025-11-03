from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.contrib import messages
from django.db.models import Q
from PIL import Image
from io import BytesIO
from .models import Category, Product, Brand, ProductVariant, ProductImage
import base64
import io

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def categories(request):
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user
    categories_list = Category.objects.all().order_by("-id")
    
    paginator = Paginator(categories_list, 3)  
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    if request.method == "POST":
        category_id = request.POST.get("category_id")  
        
        if category_id:  
            category = get_object_or_404(Category, id=category_id)
            new_name = request.POST.get("category_name", "").strip()
            
            if not new_name:
                messages.error(request, "Category name cannot be empty.")
                return redirect("admin_category")
                
            if Category.objects.filter(name__iexact=new_name).exclude(id=category_id).exists():
                messages.error(request, "This category already exists.")
                return redirect("admin_category")
            
            category.name = new_name

            if request.FILES.get("category_image"):
                category.image = request.FILES["category_image"]
            
            category.save()
            messages.success(request, f"Category '{new_name}' updated successfully.")
            return redirect("admin_category")
            
        else:  
            name = request.POST.get("category_name", "").strip()
            
            if not name:
                messages.error(request, "Category name cannot be empty.")
                return redirect("admin_category")
                
            if Category.objects.filter(name__iexact=name).exists():
                messages.error(request, "This category already exists.")
                return redirect("admin_category")
            
            
            category = Category(name=name, is_listed=True)
            
            if request.FILES.get("category_image"):
                category.image = request.FILES["category_image"]
            
            category.save()
            messages.success(request, f"Category '{name}' added successfully.")
            return redirect("admin_category")
    
    context = {
        "superusers": superusers,
        "current_super": current_super,
        "categories": categories,
        "search_query": "",
        "is_search": False,
    }
    return render(request, "admin_panel/category/category_management.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def categories_search(request):
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user
    
    search_query = request.GET.get('keyword', '').strip()
    
    if search_query:
        categories_list = Category.objects.filter(
            name__icontains=search_query
        ).order_by("-id")
    else:
        categories_list = Category.objects.all().order_by("-id")
    
    paginator = Paginator(categories_list, 3)  
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    context = {
        "superusers": superusers,
        "current_super": current_super,
        "categories": categories,
        "search_query": search_query,
        "is_search": True,
    }
    return render(request, "admin_panel/category/category_management.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def category_status(request, id, action):
    try:
        category = Category.objects.get(id=id)
        
        if action == "list":
            category.is_listed = True
            messages.success(request, f"Category '{category.name}' has been listed successfully.")
        elif action == "unlist":
            category.is_listed = False
            messages.success(request, f"Category '{category.name}' has been unlisted successfully.")
        else:
            messages.error(request, "Invalid action.")
            return redirect("admin_category")
            
        category.save()

    except Category.DoesNotExist:
        messages.error(request, "Category not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("admin_category")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def admin_products(request):
    products = Product.objects.prefetch_related("variants__images").all()
    context = {
        "products": products,
    }
    return render(request, 'admin_panel/product/product_management.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def products_search(request):
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
    return render(request, "admin_panel/product/product_management.html", context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def edit_products(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    brands = Brand.objects.filter(Q(id=product.brand.id) | Q(is_listed=True))  
    categories = Category.objects.filter(Q(id=product.category.id) | Q(is_listed=True))
    variants = product.variants.all().prefetch_related('images')

    if request.method == "POST":
        product_name = request.POST.get("product_name", "").strip()
        product_description = request.POST.get("product_description", "").strip()
        category_id = request.POST.get("product_category")
        brand_id = request.POST.get("product_brand")

        error = None

        if not product_name:
            error = "Product name is required."
        elif Product.objects.filter(name__iexact=product_name).exclude(id=product.id).exists():
            error = f"A product with the name '{product_name}' already exists."
        elif not product_description:
            error = "Product description is required."
        elif not category_id:
            error = "Please select a category."
        elif not brand_id:
            error = "Please select a brand."
        
        if error:
            context = {
                "product": product,
                "brands": brands,
                "categories": categories,
                "error": error,
                "form_data": request.POST
            }
            return render(request, "admin_panel/product/product_edit.html", context)

        variant_color_names = request.POST.getlist('variants_color_name')
        variant_color_codes = request.POST.getlist('variants_color_code')
        variant_color_hexs = request.POST.getlist('variants_color_hex')
        variant_prices = request.POST.getlist('variants_price')
        variant_stocks = request.POST.getlist('variants_stock')
        variant_is_listed = request.POST.getlist('variants_is_listed')

        cropped_main_images = request.POST.getlist('cropped_main_image')
        cropped_thumb_1 = request.POST.getlist('cropped_thumb_1')
        cropped_thumb_2 = request.POST.getlist('cropped_thumb_2')
        cropped_thumb_3 = request.POST.getlist('cropped_thumb_3')
        

        remove_main_images = request.POST.getlist('remove_main_image')
        remove_thumb_1 = request.POST.getlist('remove_thumb_1')
        remove_thumb_2 = request.POST.getlist('remove_thumb_2')
        remove_thumb_3 = request.POST.getlist('remove_thumb_3')

        for i in range(len(variant_color_names)):
            if not variant_color_names[i].strip():
                error = f"Color name is required for variant {i+1}."
                break
            try:
                price = float(variant_prices[i])
                if price < 0:
                    error = f"Price must be a positive number for variant {i+1}."
                    break
            except (ValueError, IndexError):
                error = f"Valid price is required for variant {i+1}."
                break
            
            try:
                stock = int(variant_stocks[i])
                if stock < 0:
                    error = f"Stock must be a positive number for variant {i+1}."
                    break
            except (ValueError, IndexError):
                error = f"Valid stock quantity is required for variant {i+1}."
                break

            has_main_image = False
            if i < len(cropped_main_images) and cropped_main_images[i]:
                has_main_image = True
            elif i < len(variants):
                variant = variants[i]
                main_image_exists = variant.images.exists()
                is_main_being_removed = i < len(remove_main_images) and remove_main_images[i] == 'true'
                if main_image_exists and not is_main_being_removed:
                    has_main_image = True
            
            if not has_main_image:
                error = f"Main image is required for variant {i+1}."
                break
            thumb_count = 0
            if i < len(cropped_thumb_1) and cropped_thumb_1[i]:
                thumb_count += 1
            if i < len(cropped_thumb_2) and cropped_thumb_2[i]:
                thumb_count += 1
            if i < len(cropped_thumb_3) and cropped_thumb_3[i]:
                thumb_count += 1

            if i < len(variants):
                variant = variants[i]
                existing_images = list(variant.images.all())
                if existing_images:
                    for idx, img in enumerate(existing_images[1:4]):  
                        thumb_field = f'remove_thumb_{idx+1}'
                        is_being_removed = i < len(locals().get(thumb_field, [])) and locals().get(thumb_field, [])[i] == 'true'
                        if not is_being_removed:
                            thumb_count += 1
            
            if thumb_count < 3:
                error = f"At least 3 thumbnail images are required for variant {i+1}."
                break
        
        if error:
            context = {
                "product": product,
                "brands": brands,
                "categories": categories,
                "error": error,
                "form_data": request.POST
            }
            return render(request, "admin_panel/product/product_edit.html", context)
        
        
        try:
            category = Category.objects.get(id=category_id)
            brand = Brand.objects.get(id=brand_id)
            
            product.name = product_name
            product.description = product_description
            product.category = category
            product.brand = brand
            product.save()

            existing_variants = list(variants)
            
            for i in range(len(variant_color_names)):
                if i < len(existing_variants):
                    variant = existing_variants[i]
                else:
                    variant = ProductVariant.objects.create(product=product)
                
                variant.color_name = variant_color_names[i]
                if i < len(variant_color_codes):
                    variant.color_code = variant_color_codes[i]
                elif i < len(variant_color_hexs):
                    variant.color_code = variant_color_hexs[i]
                else:
                    variant.color_code = "#000000"
                    
                variant.price = float(variant_prices[i])
                variant.stock = int(variant_stocks[i])
                variant.is_listed = variant_is_listed[i].lower() == 'true' if i < len(variant_is_listed) else True
                variant.save()
                
                existing_images = list(variant.images.all())

                if i < len(remove_main_images) and remove_main_images[i] == 'true':
                    if existing_images:
                        existing_images[0].delete()
                        existing_images = existing_images[1:]
                
                if i < len(cropped_main_images) and cropped_main_images[i]:
                    if existing_images and not (i < len(remove_main_images) and remove_main_images[i] == 'true'):
                        existing_images[0].delete()
                        existing_images = existing_images[1:]

                    image_file = process_base64_image(
                        cropped_main_images[i],
                        f"{product_name}_variant_{i+1}_main"
                    )
                    if image_file:
                        ProductImage.objects.create(variant=variant, image=image_file)
                
                thumb_data = [
                    cropped_thumb_1[i] if i < len(cropped_thumb_1) else None,
                    cropped_thumb_2[i] if i < len(cropped_thumb_2) else None,
                    cropped_thumb_3[i] if i < len(cropped_thumb_3) else None
                ]
                
                remove_thumb_data = [
                    remove_thumb_1[i] if i < len(remove_thumb_1) else None,
                    remove_thumb_2[i] if i < len(remove_thumb_2) else None,
                    remove_thumb_3[i] if i < len(remove_thumb_3) else None
                ]
                
                current_thumbs = existing_images[1:] if len(existing_images) > 1 else []
                
                for thumb_idx in range(3):
                    if remove_thumb_data[thumb_idx] == 'true' and thumb_idx < len(current_thumbs):
                        current_thumbs[thumb_idx].delete()
                    if thumb_data[thumb_idx]:
                        if thumb_idx < len(current_thumbs) and remove_thumb_data[thumb_idx] != 'true':
                            current_thumbs[thumb_idx].delete()
                        
                        image_file = process_base64_image(
                            thumb_data[thumb_idx],
                            f"{product_name}_variant_{i+1}_thumb_{thumb_idx+1}"
                        )
                        if image_file:
                            ProductImage.objects.create(variant=variant, image=image_file)
            if len(existing_variants) > len(variant_color_names):
                for i in range(len(variant_color_names), len(existing_variants)):
                    existing_variants[i].delete()
            
            messages.success(request, "Product updated successfully!")
            return redirect("admin_products")
            
        except Exception as e:
            error = f"Error updating product: {str(e)}"
            context = {
                "product": product,
                "brands": brands,
                "categories": categories,
                "error": error,
                "form_data": request.POST
            }
            return render(request, "admin_panel/product/product_edit.html", context)
    context = {
        "product": product,
        "brands": brands,
        "categories": categories,
    }
    return render(request, "admin_panel/product/product_edit.html", context)



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def add_products(request):
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

def validate_cropped_image(base64_data, expected_width=400, expected_height=500):
    """
    Validate that the cropped image has the expected dimensions
    """
    try:
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))
        
        return image.size == (expected_width, expected_height)
    except:
        return False

def product_variant(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.prefetch_related("images").filter(is_listed=True)

    return render(request, "admin_panel/product/product_variant.html", {
        "product": product,
        "variants": variants
    })

