from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.urls import reverse
from userlogin.models import CustomUser
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model


# Admin Login
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_index')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect("admin_index")
            else:
                messages.error(request, "You don't have access to the Admin Panel.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "admin_panel/admin_login.html")


# Admin Logout
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def admin_logout(request):
    request.session.flush()
    return redirect("admin_login")


# List Users
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def users(request):
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user
    
    users = CustomUser.objects.exclude(is_superuser=True).order_by("-created_at")
    paginator = Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_users = paginator.get_page(page)

    context = {
        "users": page_users,
        "superusers": superusers,
        "current_super": current_super,
        "is_search": False,
        "keyword": "",
    }
    return render(request, "admin_panel/user_list/users_management.html", context)


# Change User status Block / Unblock
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def user_status(request, id):
    try:
        user = CustomUser.objects.get(id=id)
        if not user.is_superuser:  
            user.is_active = not user.is_active
            user.save()
            
            action = "unblocked" if user.is_active else "blocked"
            messages.success(request, f"User {user.fullname} has been {action} successfully.")
        else:
            messages.error(request, "Cannot modify superuser status.")
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")

    keyword = request.GET.get("keyword", "").strip()
    page = request.GET.get("page", 1)

    if keyword:
        return redirect(f"{reverse('users_search')}?keyword={keyword}&page={page}")
    else:
        return redirect(f"{reverse('admin_users')}?page={page}")


# Search Users
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def users_search(request):
    keyword = request.GET.get("keyword", "").strip()
    message = None
    users = CustomUser.objects.none() 

    if keyword:
        users = CustomUser.objects.filter(
            Q(id__icontains=keyword) |
            Q(fullname__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(phone__icontains=keyword) |
            Q(created_at__date__icontains=keyword)
        ).exclude(is_superuser=True).order_by("-created_at")

        if not users.exists():
            message = f"No users found matching '{keyword}'"
    else:
        return redirect('admin_users')

    paginator = Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_users = paginator.get_page(page)

    context = {
        "users": page_users,
        "message": message,
        "keyword": keyword,
        "is_search": True,
        "total_results": users.count() if keyword else 0,
    }
    return render(request, "admin_panel/user_list/users_management.html", context)
