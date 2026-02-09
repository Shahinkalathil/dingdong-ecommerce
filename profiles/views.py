from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import CustomUser
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from .models import Address
from orders.models import Order
from django.urls import reverse
import re
import logging
from django.views.decorators.http import require_http_methods
from wallet.models import Wallet

@login_required
def OverView(request):
    user = request.user
    addresses = user.addresses.all()
    total_orders = Order.objects.count()
    recent_orders = Order.objects.filter(user=user).prefetch_related(
        'items__variant__images'
    ).select_related('delivery_address')[:4]
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    context = {
        "show_sidebar": True,
        "user": user,
        "last_login": user.last_login,
        "addresses": addresses,
        "total_orders": total_orders,
        "recent_orders": recent_orders,
        'wallet' : wallet,
    }
    return render(request, 'user_side/profile/overview.html', context)

logger = logging.getLogger(__name__)
@login_required
@require_http_methods(["POST"])
def ChangePasswordView(request):
    """
    Handle password change via AJAX request
    """
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False, 
            'errors': {'general': 'Invalid request'}
        }, status=400)
    old_password = request.POST.get('oldPassword', '').strip()
    new_password = request.POST.get('newPassword', '').strip()
    confirm_password = request.POST.get('confirmPassword', '').strip()
    
    errors = {}
    logger.info(f"Password change attempt by user: {request.user.username}")
    if not old_password:
        errors['oldPassword'] = "Old password is required"
    else:
        if not request.user.check_password(old_password):
            errors['oldPassword'] = "Old password is incorrect"
            logger.warning(f"Incorrect old password for user: {request.user.username}")
    if not new_password:
        errors['newPassword'] = "New password is required"
    elif len(new_password) < 8:
        errors['newPassword'] = "Password must be at least 8 characters long"
    elif not any(char.isdigit() for char in new_password):
        errors['newPassword'] = "Password must contain at least one number"
    elif not any(char.isupper() for char in new_password):
        errors['newPassword'] = "Password must contain at least one uppercase letter"
    elif old_password and new_password == old_password:
        errors['newPassword'] = "New password must be different from old password"
    if not confirm_password:
        errors['confirmPassword'] = "Please confirm your new password"
    elif new_password and confirm_password != new_password:
        errors['confirmPassword'] = "Passwords do not match"
    if errors:
        logger.info(f"Password change validation failed for {request.user.username}: {errors}")
        return JsonResponse({
            'success': False, 
            'errors': errors
        })
    try:

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        logger.info(f"Password changed successfully for user: {request.user.username}")
        return JsonResponse({
            'success': True, 
            'message': 'Password changed successfully!'
        })
        
    except Exception as e:
        logger.error(f"Error changing password for {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False, 
            'errors': {'general': 'An error occurred. Please try again.'}
        })

@login_required
def ProfileUpdateView(request, id):
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
def AddressCreateView(request):
    next_url = request.GET.get('next', None)
    if request.method == 'POST':
        errors = {}
        is_valid = True
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

        if not country:
            is_valid = False
            errors["country"] = "Please select a country"
            messages.error(request, errors["country"])

        elif country not in dict(Address.COUNTRY_CHOICES):
            is_valid = False
            errors["country"] = "Please select a valid country"
            messages.error(request, errors["country"])
        
        elif not full_name:
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
        
        if not mobile_number:
            is_valid = False
            errors["mobile_number"] = "Mobile number is required"
            messages.error(request, errors["mobile_number"])
        elif not re.fullmatch(r'^\d{10,15}$', mobile_number):
            is_valid = False
            errors["mobile_number"] = "Mobile number must contain 10-15 digits only"
            messages.error(request, errors["mobile_number"])
        
        if not pincode:
            is_valid = False
            errors["pincode"] = "Pincode is required"
            messages.error(request, errors["pincode"])
        elif not re.fullmatch(r'^\d{6}$', pincode):
            is_valid = False
            errors["pincode"] = "Pincode must be exactly 6 digits"
            messages.error(request, errors["pincode"])
        
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
        
        if landmark and len(landmark) > 100:
            is_valid = False
            errors["landmark"] = "Landmark must not exceed 100 characters"
            messages.error(request, errors["landmark"])
        
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

        if not state or state == 'Select':
            is_valid = False
            errors["state"] = "Please select a state"
            messages.error(request, errors["state"])
        elif state not in dict(Address.STATE_CHOICES):
            is_valid = False
            errors["state"] = "Please select a valid state"
            messages.error(request, errors["state"])

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
                if is_default:
                    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                else:
                    if not Address.objects.filter(user=request.user).exists():
                        is_default = True
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
                if next_url:
                    return redirect(next_url)
                return redirect('profile')
                
            except Exception as e:
                messages.error(request, f"An error occurred while saving the address: {str(e)}")
                return render(request, 'user_side/profile/add_address.html', {
                    'errors': errors,
                    'form_data': request.POST,
                    'next': next_url, 
                })
        else:
            return render(request, 'user_side/profile/add_address.html', {
                'errors': errors,
                'form_data': request.POST,
                'next': next_url, 
            })
    return render(request, 'user_side/profile/add_address.html', {'next': next_url,})

@login_required
def AddressUpdateView(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    next_url = request.GET.get('next', reverse('profile'))
    
    if request.method == 'POST':
        next_url = request.POST.get('next', next_url)
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
        
        errors = {}
        
        if not country or country == 'Select Country':
            errors['country'] = 'Please select a country'

        if not full_name:
            errors['full_name'] = 'Full name is required'
        elif len(full_name) < 2:
            errors['full_name'] = 'Full name must be at least 2 characters'
        elif not re.match(r'^[a-zA-Z\s]+$', full_name):
            errors['full_name'] = 'Full name should only contain letters and spaces'

        if not mobile_number:
            errors['mobile_number'] = 'Mobile number is required'
        elif not re.match(r'^[0-9]{10,15}$', mobile_number):
            errors['mobile_number'] = 'Mobile number must be 10-15 digits'
        
        if not pincode:
            errors['pincode'] = 'Pincode is required'
        elif not re.match(r'^[0-9]{6}$', pincode):
            errors['pincode'] = 'Pincode must be 6 digits'

        if not area_street:
            errors['area_street'] = 'Area/Street is required'
        elif len(area_street) < 3:
            errors['area_street'] = 'Area/Street must be at least 3 characters'

        if not flat_house:
            errors['flat_house'] = 'Flat/House details are required'
        elif len(flat_house) < 2:
            errors['flat_house'] = 'Flat/House details must be at least 2 characters'

        if not town_city:
            errors['town_city'] = 'Town/City is required'
        elif len(town_city) < 2:
            errors['town_city'] = 'Town/City must be at least 2 characters'
        elif not re.match(r'^[a-zA-Z\s]+$', town_city):
            errors['town_city'] = 'Town/City should only contain letters and spaces'

        if not state or state == 'Select':
            errors['state'] = 'Please select a state'

        if not address_type:
            errors['address_type'] = 'Please select an address type'
        
        if not errors:
            duplicate = Address.objects.filter(
                user=request.user,
                country=country,
                full_name=full_name,
                mobile_number=mobile_number,
                pincode=pincode,
                area_street=area_street,
                flat_house=flat_house,
                town_city=town_city,
                state=state
            ).exclude(id=address_id).exists()
            
            if duplicate:
                errors['duplicate'] = 'This address already exists'
                messages.error(request, 'This address already exists in your saved addresses.')
        if errors:
            context = {
                'address': address,
                'errors': errors,
                'form_data': {
                    'country': country,
                    'full_name': full_name,
                    'mobile_number': mobile_number,
                    'pincode': pincode,
                    'area_street': area_street,
                    'flat_house': flat_house,
                    'landmark': landmark,
                    'town_city': town_city,
                    'state': state,
                    'address_type': address_type,
                    'is_default': is_default,
                    'next': next_url,
                }
            }
            return render(request, 'user_side/profile/edit_address.html', context)
        try:
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
            
            messages.success(request, f'{address_type} address updated successfully!')
            return redirect(next_url)
            
        except Exception as e:
            messages.error(request, f'Error updating address: {str(e)}')
            context = {
                'address': address,
                'errors': {},
                'form_data': {
                    'country': country,
                    'full_name': full_name,
                    'mobile_number': mobile_number,
                    'pincode': pincode,
                    'area_street': area_street,
                    'flat_house': flat_house,
                    'landmark': landmark,
                    'town_city': town_city,
                    'state': state,
                    'address_type': address_type,
                    'is_default': is_default,
                    'next': next_url,
                }
            }
            return render(request, 'user_side/profile/edit_address.html', context)
    context = {
        'address': address,
        'errors': {},
        'form_data': {},
        'next': next_url,
    }
    return render(request, 'user_side/profile/edit_address.html', context)

@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if address.is_default:
        messages.info(request, 'This address is already your default address.')
        return redirect('profile')
    
    try:
        address.is_default = True
        address.save()
        
        messages.success(
            request, 
            f'{address.address_type} address has been set as your default address.'
        )
    except Exception as e:
        messages.error(request, f'Error setting default address: {str(e)}')
    
    return redirect('profile')

@login_required
def AddressDeleteView(request, address_id):
    """
    Delete an address with proper handling of default address transfer
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if Address.objects.filter(user=request.user).count() == 1:
        messages.warning(request, 'You cannot delete your only address. Please add another address first.')
        return redirect('profile')
    address_type = address.address_type
    is_default = address.is_default
    
    try:
        address.delete()
        if is_default:
            messages.success(
                request, 
                f'{address_type} address deleted successfully. Another address has been set as default.'
            )
        else:
            messages.success(request, f'{address_type} address deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting address: {str(e)}')
    
    return redirect('profile')


