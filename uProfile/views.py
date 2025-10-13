from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from userlogin.models import CustomUser
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash


# Create your views here.
@login_required
def overview(request):
    user = request.user
    context = {
        "show_sidebar": True,
        "user" : user,
        "last_login": user.last_login,
    }
    return render(request, 'user_side/profile/overview.html', context)

@login_required
def change_password(request):
    if request.method == "POST":
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            old = request.POST.get('oldPassword')
            new = request.POST.get('newPassword')
            confirm = request.POST.get('confirmPassword')
            errors = {}

            if not old:
                errors['oldPassword'] = "Old password is required"
            elif not request.user.check_password(old):
                errors['oldPassword'] = "Old password is incorrect"
            
            if not new:
                errors['newPassword'] = "New password is required"
            elif len(new) < 8:
                errors['newPassword'] = "Password must be at least 8 characters long"
            elif new == old:
                errors['newPassword'] = "New password must be different from old password"

            if not confirm:
                errors['confirmPassword'] = "Please confirm your new password"
            elif new != confirm:
                errors['confirmPassword'] = "Passwords do not match"

            if errors:
                return JsonResponse({'success': False, 'errors': errors})

            request.user.set_password(new)
            request.user.save()

            update_session_auth_hash(request, request.user)
            
            return JsonResponse({
                'success': True, 
                'message': 'Password changed successfully!'
            })
        
    return redirect('profile')




@login_required
def edit_profile(request, id):
    user = get_object_or_404(CustomUser, id=id)
    if user != request.user:
        return redirect("profile")
    try:
        if request.method == "POST":
            fullname = request.POST.get("fullname")
            phone = request.POST.get("phone")
            gender = request.POST.get("gender")
            dob = request.POST.get("dob")
            location = request.POST.get("location")

            
            if not fullname or not phone or not dob or not location:
                messages.error(request, "Please fill all required fields")
                return redirect("edit_profile", id=id)

            
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.fullname = fullname
            user.phone = phone
            user.alt_phone = request.POST.get("alt_phone")
            user.gender = gender
            user.dob = dob
            user.location = location
            user.save()

            messages.success(request, "Profile updated successfully")
            return redirect("profile")

    except Exception as e:
        messages.error(request, "Something went wrong, please try again.")
    
    context = {
        "show_sidebar": False,
        'user' : user
    } 
    return render(request, 'user_side/profile/edit_profile.html', context)

def add_address(request):
    return render(request, 'user_side/profile/add_address.html')

def edit_address(request):
    return render(request, 'user_side/profile/edit_address.html')


def order(request):
    return render(request, 'user_side/profile/order.html')


def order_detail(request):
    return render(request, 'user_side/profile/order_detail.html')
