from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from userlogin.models import CustomUser
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from .models import Address
import re


# Create your views here.
@login_required
def overview(request):
    user = request.user
    addresses = user.addresses.all()
    context = {
        "show_sidebar": True,
        "user" : user,
        "last_login": user.last_login,
        "addresses" : addresses,
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

@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    request.user.addresses.update(is_default=False)
    address.is_default = True
    address.save()

    messages.success(request, "Default address updated successfully.")
    return redirect('profile')  

@login_required
def add_address(request):
    if request.method == 'POST':
        errors = {}
        is_valid = True
        
        # Get form data
        country = request.POST.get('country', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        area_street = request.POST.get('area_street', '').strip()
        flat_house = request.POST.get('flat_house', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        town_city = request.POST.get('town_city', '').strip()
        state = request.POST.get('state', '').strip()
        address_type = request.POST.get('address_type', '').strip()
        is_default = request.POST.get('is_default') == 'on'
        
        # Validation for country
        if not country:
            is_valid = False
            errors["country"] = "Please select a country"
            messages.error(request, errors["country"])
        elif country not in dict(Address.COUNTRY_CHOICES):
            is_valid = False
            errors["country"] = "Please select a valid country"
            messages.error(request, errors["country"])
        
        # Validation for full name
        if not full_name:
            is_valid = False
            errors["full_name"] = "Full name is required"
            messages.error(request, errors["full_name"])
        elif len(full_name) < 3:
            is_valid = False
            errors["full_name"] = "Full name must be at least 3 characters long"
            messages.error(request, errors["full_name"])
        elif len(full_name) > 100:
            is_valid = False
            errors["full_name"] = "Full name must not exceed 100 characters"
            messages.error(request, errors["full_name"])
        elif not re.fullmatch(r'^[a-zA-Z\s.]+$', full_name):
            is_valid = False
            errors["full_name"] = "Full name can only contain letters, spaces, and dots"
            messages.error(request, errors["full_name"])
        
        # Validation for mobile number
        if not mobile_number:
            is_valid = False
            errors["mobile_number"] = "Mobile number is required"
            messages.error(request, errors["mobile_number"])
        elif not re.fullmatch(r'^\d{10,15}$', mobile_number):
            is_valid = False
            errors["mobile_number"] = "Mobile number must contain 10-15 digits only"
            messages.error(request, errors["mobile_number"])
        
        # Validation for pincode
        if not pincode:
            is_valid = False
            errors["pincode"] = "Pincode is required"
            messages.error(request, errors["pincode"])
        elif not re.fullmatch(r'^\d{6}$', pincode):
            is_valid = False
            errors["pincode"] = "Pincode must be exactly 6 digits"
            messages.error(request, errors["pincode"])
        
        # Validation for area/street
        if not area_street:
            is_valid = False
            errors["area_street"] = "Area/Street is required"
            messages.error(request, errors["area_street"])
        elif len(area_street) < 3:
            is_valid = False
            errors["area_street"] = "Area/Street must be at least 3 characters long"
            messages.error(request, errors["area_street"])
        elif len(area_street) > 255:
            is_valid = False
            errors["area_street"] = "Area/Street must not exceed 255 characters"
            messages.error(request, errors["area_street"])
        
        # Validation for flat/house
        if not flat_house:
            is_valid = False
            errors["flat_house"] = "Flat/House number is required"
            messages.error(request, errors["flat_house"])
        elif len(flat_house) < 2:
            is_valid = False
            errors["flat_house"] = "Flat/House number must be at least 2 characters long"
            messages.error(request, errors["flat_house"])
        elif len(flat_house) > 255:
            is_valid = False
            errors["flat_house"] = "Flat/House number must not exceed 255 characters"
            messages.error(request, errors["flat_house"])
        
        # Validation for landmark (optional)
        if landmark and len(landmark) > 100:
            is_valid = False
            errors["landmark"] = "Landmark must not exceed 100 characters"
            messages.error(request, errors["landmark"])
        
        # Validation for town/city
        if not town_city:
            is_valid = False
            errors["town_city"] = "Town/City is required"
            messages.error(request, errors["town_city"])
        elif len(town_city) < 2:
            is_valid = False
            errors["town_city"] = "Town/City must be at least 2 characters long"
            messages.error(request, errors["town_city"])
        elif len(town_city) > 100:
            is_valid = False
            errors["town_city"] = "Town/City must not exceed 100 characters"
            messages.error(request, errors["town_city"])
        elif not re.fullmatch(r'^[a-zA-Z\s.]+$', town_city):
            is_valid = False
            errors["town_city"] = "Town/City can only contain letters, spaces, and dots"
            messages.error(request, errors["town_city"])
        
        # Validation for state
        if not state or state == 'Select':
            is_valid = False
            errors["state"] = "Please select a state"
            messages.error(request, errors["state"])
        elif state not in dict(Address.STATE_CHOICES):
            is_valid = False
            errors["state"] = "Please select a valid state"
            messages.error(request, errors["state"])
        
        # Validation for address type
        if not address_type:
            is_valid = False
            errors["address_type"] = "Please select an address type"
            messages.error(request, errors["address_type"])
        elif address_type not in dict(Address.ADDRESS_TYPE_CHOICES):
            is_valid = False
            errors["address_type"] = "Please select a valid address type"
            messages.error(request, errors["address_type"])
        
        
        if is_valid:
            try:
                # Handle default address logic
                if is_default:
                    # Remove default flag from all other addresses of this user
                    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                else:
                    # If this is the first address, make it default automatically
                    if not Address.objects.filter(user=request.user).exists():
                        is_default = True
                
                # Create the address
                address = Address.objects.create(
                    user=request.user,
                    country=country,
                    full_name=full_name,
                    mobile_number=mobile_number,
                    pincode=pincode,
                    area_street=area_street,
                    flat_house=flat_house,
                    landmark=landmark if landmark else None,
                    town_city=town_city,
                    state=state,
                    address_type=address_type,
                    is_default=is_default
                )
                
                messages.success(request, "Address added successfully!")
                return redirect('profile')  # Redirect to profile page
                
            except Exception as e:
                messages.error(request, f"An error occurred while saving the address: {str(e)}")
                return render(request, 'user_side/profile/add_address.html', {
                    'errors': errors,
                    'form_data': request.POST
                })
        else:
            # Return form with errors
            return render(request, 'user_side/profile/add_address.html', {
                'errors': errors,
                'form_data': request.POST
            })
    
    
    return render(request, 'user_side/profile/add_address.html')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        errors = {}
        is_valid = True
        
        # Get form data
        country = request.POST.get('country', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        area_street = request.POST.get('area_street', '').strip()
        flat_house = request.POST.get('flat_house', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        town_city = request.POST.get('town_city', '').strip()
        state = request.POST.get('state', '').strip()
        address_type = request.POST.get('address_type', '').strip()
        is_default = request.POST.get('is_default') == 'on'
        
        # Validation for country
        if not country:
            is_valid = False
            errors["country"] = "Please select a country"
            messages.error(request, errors["country"])
        elif country not in dict(Address.COUNTRY_CHOICES):
            is_valid = False
            errors["country"] = "Please select a valid country"
            messages.error(request, errors["country"])
        
        # Validation for full name
        if not full_name:
            is_valid = False
            errors["full_name"] = "Full name is required"
            messages.error(request, errors["full_name"])
        elif len(full_name) < 3:
            is_valid = False
            errors["full_name"] = "Full name must be at least 3 characters long"
            messages.error(request, errors["full_name"])
        elif len(full_name) > 100:
            is_valid = False
            errors["full_name"] = "Full name must not exceed 100 characters"
            messages.error(request, errors["full_name"])
        elif not re.fullmatch(r'^[a-zA-Z\s.]+$', full_name):
            is_valid = False
            errors["full_name"] = "Full name can only contain letters, spaces, and dots"
            messages.error(request, errors["full_name"])
        
        # Validation for mobile number
        if not mobile_number:
            is_valid = False
            errors["mobile_number"] = "Mobile number is required"
            messages.error(request, errors["mobile_number"])
        elif not re.fullmatch(r'^\d{10,15}$', mobile_number):
            is_valid = False
            errors["mobile_number"] = "Mobile number must contain 10-15 digits only"
            messages.error(request, errors["mobile_number"])
        
        # Validation for pincode
        if not pincode:
            is_valid = False
            errors["pincode"] = "Pincode is required"
            messages.error(request, errors["pincode"])
        elif not re.fullmatch(r'^\d{6}$', pincode):
            is_valid = False
            errors["pincode"] = "Pincode must be exactly 6 digits"
            messages.error(request, errors["pincode"])
        
        # Validation for area/street
        if not area_street:
            is_valid = False
            errors["area_street"] = "Area/Street is required"
            messages.error(request, errors["area_street"])
        elif len(area_street) < 3:
            is_valid = False
            errors["area_street"] = "Area/Street must be at least 3 characters long"
            messages.error(request, errors["area_street"])
        elif len(area_street) > 255:
            is_valid = False
            errors["area_street"] = "Area/Street must not exceed 255 characters"
            messages.error(request, errors["area_street"])
        
        # Validation for flat/house
        if not flat_house:
            is_valid = False
            errors["flat_house"] = "Flat/House number is required"
            messages.error(request, errors["flat_house"])
        elif len(flat_house) < 2:
            is_valid = False
            errors["flat_house"] = "Flat/House number must be at least 2 characters long"
            messages.error(request, errors["flat_house"])
        elif len(flat_house) > 255:
            is_valid = False
            errors["flat_house"] = "Flat/House number must not exceed 255 characters"
            messages.error(request, errors["flat_house"])
        
        # Validation for landmark (optional)
        if landmark and len(landmark) > 100:
            is_valid = False
            errors["landmark"] = "Landmark must not exceed 100 characters"
            messages.error(request, errors["landmark"])
        
        # Validation for town/city
        if not town_city:
            is_valid = False
            errors["town_city"] = "Town/City is required"
            messages.error(request, errors["town_city"])
        elif len(town_city) < 2:
            is_valid = False
            errors["town_city"] = "Town/City must be at least 2 characters long"
            messages.error(request, errors["town_city"])
        elif len(town_city) > 100:
            is_valid = False
            errors["town_city"] = "Town/City must not exceed 100 characters"
            messages.error(request, errors["town_city"])
        elif not re.fullmatch(r'^[a-zA-Z\s.]+$', town_city):
            is_valid = False
            errors["town_city"] = "Town/City can only contain letters, spaces, and dots"
            messages.error(request, errors["town_city"])
        
        # Validation for state
        if not state or state == 'Select':
            is_valid = False
            errors["state"] = "Please select a state"
            messages.error(request, errors["state"])
        elif state not in dict(Address.STATE_CHOICES):
            is_valid = False
            errors["state"] = "Please select a valid state"
            messages.error(request, errors["state"])
        
        # Validation for address type
        if not address_type:
            is_valid = False
            errors["address_type"] = "Please select an address type"
            messages.error(request, errors["address_type"])
        elif address_type not in dict(Address.ADDRESS_TYPE_CHOICES):
            is_valid = False
            errors["address_type"] = "Please select a valid address type"
            messages.error(request, errors["address_type"])
        
        # Check for duplicate addresses (exclude current address)
        duplicate_check = Address.objects.filter(
            user=request.user,
            country=country,
            full_name=full_name,
            mobile_number=mobile_number,
            pincode=pincode,
            area_street=area_street,
            flat_house=flat_house,
            town_city=town_city,
            state=state
        ).exclude(id=address_id)
        
        if duplicate_check.exists():
            is_valid = False
            errors["duplicate"] = "This address already exists in your saved addresses"
            messages.error(request, errors["duplicate"])
        
        # If all validations pass, update the address
        if is_valid:
            try:
                # Handle default address logic
                if is_default and not address.is_default:
                    # Remove default flag from all other addresses
                    Address.objects.filter(user=request.user, is_default=True).exclude(id=address_id).update(is_default=False)
                elif not is_default and address.is_default:
                    # Check if this is the only address
                    if Address.objects.filter(user=request.user).count() == 1:
                        is_default = True
                        messages.warning(request, "Cannot remove default status from your only address")
                    else:
                        # Make the next most recent address default
                        next_default = Address.objects.filter(user=request.user).exclude(id=address_id).first()
                        if next_default:
                            next_default.is_default = True
                            next_default.save()
                address.country = country
                address.full_name = full_name
                address.mobile_number = mobile_number
                address.pincode = pincode
                address.area_street = area_street
                address.flat_house = flat_house
                address.landmark = landmark if landmark else None
                address.town_city = town_city
                address.state = state
                address.address_type = address_type
                address.is_default = is_default
                address.save()
                
                messages.success(request, "Address updated successfully!")
                return redirect('profile')
                
            except Exception as e:
                messages.error(request, f"An error occurred while updating the address: {str(e)}")
                return render(request, 'user_side/profile/edit_address.html', {
                    'address': address,
                    'errors': errors,
                    'form_data': request.POST
                })
        else:
           
            return render(request, 'user_side/profile/edit_address.html', {
                'address': address,
                'errors': errors,
                'form_data': request.POST
            })
    
    
    return render(request, 'user_side/profile/edit_address.html', {
        'address': address
    })


def order(request):
    return render(request, 'user_side/profile/order.html')


def order_detail(request):
    return render(request, 'user_side/profile/order_detail.html')
