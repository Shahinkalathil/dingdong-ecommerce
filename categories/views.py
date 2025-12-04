from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.contrib import messages
from products.models import Category


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def AdminCategoryListView(request):
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
def AdminSearchView(request):
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
