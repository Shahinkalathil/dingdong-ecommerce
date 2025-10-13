from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from userlogin.models import CustomUser


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
    user = request.user
    if request.method == "POST":
        old_password = request.POST.get("oldPassword")
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmPassword") 




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
