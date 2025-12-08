from django.shortcuts import render, redirect, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from .models import CustomUser
from .utils import send_otp_email, send_forget_password_mail, redirect_authenticated
from django.views.decorators.cache import never_cache
import random
import re
import uuid

@redirect_authenticated
@never_cache
def sign_up(request):
    if request.method == "POST":
        fullname = request.POST.get("fullname").strip()
        phone = request.POST.get("phone").strip()
        email = request.POST.get("email").strip().lower()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirmPassword")

        errors = {}
        is_valid = True
        
        # full name errors
        if not fullname:
            is_valid = False
            errors["fullname"] = "Please enter your full name"
            messages.error(request, errors["fullname"])

        # email
        if not email:
            is_valid = False
            errors["email"] = "Please enter your email"
            messages.error(request, errors["email"])

        # phone
        if not phone:
            is_valid = False
            errors["phone"] = "Please enter your phone number"
            messages.error(request, errors["phone"])

        # password
        if not password:
            is_valid = False
            errors["password"] = "Please enter a password"
            messages.error(request, errors["password"])
        
        for m in messages.get_messages(request):
            print(f"[{m.level_tag.upper()}] {m.message}")

        # valid
        if not is_valid:
            return render(request, "user_side/auth/sign_up.html", {
                "fullname": fullname,
                "phone": phone,
                "email": email,
                "errors": errors,
                
            })


        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if fullname and (len(fullname) < 3 or len(fullname) > 50):
            is_valid = False
            errors["fullname"] = "Full name must be between 3 and 50 characters"
            messages.error(request, errors["fullname"])
        
        if fullname and not re.fullmatch(r"^[A-Za-z]+(?: [A-Za-z]+)*$", fullname):
            is_valid = False
            errors["fullname"] = "Full name should only contain letters and spaces"
            messages.error(request, errors["fullname"])
        if not re.fullmatch(email_pattern, email):
            is_valid = False
            errors["email"] = "Please enter a valid email address"
            messages.error(request, errors["email"])

        if not re.fullmatch(r'^\d{10,15}$', phone):
            is_valid = False
            errors["phone"] = "Phone number must contain only digits (10–15 digits)"
            messages.error(request, errors["phone"])

        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user and existing_user.is_active:
            is_valid = False
            errors["email"] = "Email is already taken"
            messages.error(request, errors["email"])

        if CustomUser.objects.filter(phone=phone).exclude(email=email).exists():
            is_valid = False
            errors["phone"] = "Phone number is already taken"
            messages.error(request, errors["phone"])

        if CustomUser.objects.filter(fullname__iexact=fullname).exclude(email=email).exists():
            is_valid = False
            errors["fullname"] = "Full name is already taken"
            messages.error(request, errors["fullname"])

        pw_errors = []
        if len(password) < 8:
            pw_errors.append("at least 8 characters")
        if not re.search(r"[a-z]", password):
            pw_errors.append("one lowercase letter")
        if not re.search(r"[A-Z]", password):
            pw_errors.append("one uppercase letter")
        if not re.search(r"[0-9]", password):
            pw_errors.append("one number")
        if not re.search(r"[@$!%*?&]", password):
            pw_errors.append("one special character (@$!%*?&)")
        if pw_errors:
            is_valid = False
            errors["password"] = "Password must contain: " + ", ".join(pw_errors)
            messages.error(request, errors["password"])

        if password != confirm_password:
            is_valid = False
            errors["confirmPassword"] = "Passwords do not match"
            messages.error(request, errors["confirmPassword"])

        if not is_valid:
            return render(request, "user_side/auth/sign_up.html", {
                "fullname": fullname,
                "phone": phone,
                "email": email,
                "errors": errors,
            })

        otp_sent = str(random.randint(100000, 999999))
        otp_expiry = now() + timedelta(seconds=60)

        if existing_user and not existing_user.is_active:
            existing_user.fullname = fullname
            existing_user.phone = phone
            existing_user.set_password(password)
            existing_user.otp = otp_sent
            existing_user.otp_expiry = otp_expiry
            existing_user.save()
            user = existing_user
        else:
            user = CustomUser.objects.create_user(
                username=email,
                phone=phone,
                email=email,
                password=password,
                fullname=fullname,
                is_active=False,
                otp=otp_sent,
                otp_expiry=otp_expiry,
            )

        send_otp_email(email, otp_sent)
        request.session["email"] = email
        request.session["user_id"] = user.id
        return redirect("otp")
    return render(request, 'user_side/auth/sign_up.html')


def otp(request):
    if "user_id" not in request.session:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("sign_up")
    
    try:
        user = CustomUser.objects.get(id=request.session["user_id"])
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found. Please sign up again.")
        return redirect("sign_up")
    

    otp_expiry = user.otp_expiry

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        if entered_otp != user.otp:
            messages.error(request, "Invalid OTP")
            return redirect("otp")
        else:
            user.is_active = True
            user.otp = None  
            user.save()

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            return redirect("home")

    return render(request, "user_side/auth/otp.html", {"otp_expiry": otp_expiry, "user": user})

@redirect_authenticated
@never_cache
def sign_in(request):
    email = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        User = get_user_model()
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            request.session['email'] = user.email
            return redirect('home')
        else:
            try:
                user_obj = User.objects.get(email=email)
                if not user_obj.is_active:
                    messages.error(request, 'Your account has been blocked by admin. Send email to shahinluttu@gmail.com')
                else:
                    messages.error(request, 'Invalid email or password')
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password')
        return render(request, 'user_side/auth/sign_in.html', {'email': email})
    return render(request, 'user_side/auth/sign_in.html', {'email': email})


def resend_otp(request):
    user = CustomUser.objects.get(id=request.session["user_id"])
    otp_sent = str(random.randint(100000, 999999))
    otp_expiry = now() + timedelta(seconds=60)

    user.otp = otp_sent
    user.otp_expiry = otp_expiry
    user.save()
    send_otp_email(user.email, otp_sent)
    messages.success(request, "A new OTP has been sent to your email")
    return redirect("otp")


def forgot_email_check(request):
    email_sent = False
    reset_done = request.GET.get("reset_done", False)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        user = CustomUser.objects.filter(email=email, is_active=True).first()
        if user:
            token = str(uuid.uuid4())
            user.forget_password_token = token
            user.forget_password_expiry = timezone.now() + timedelta(minutes=15)
            user.save()
            send_forget_password_mail(email, token, request)
            email_sent = True
            messages.success(request, "Check your email for the password reset link.")
        else:
            messages.error(request, "Email not registered. Sign in?")
    return render(request, "user_side/auth/forgot_email_check.html", {"email_sent": email_sent, "reset_done": reset_done})


def reset_password(request):
    token = request.GET.get("token", "")
    if not token:
        messages.error(request, "Invalid or missing token")
        return redirect("forgot_email_check")

    user = CustomUser.objects.filter(forget_password_token=token, is_active=True).first()
    if not user or timezone.now() > user.forget_password_expiry:
        messages.error(request, "Token expired or invalid")
        return redirect("forgot_email_check")

    if request.method == "POST":
        password = request.POST.get("password")
        if user.check_password(password):
            messages.error(request, "You cannot reuse your previous password!")
            return redirect("reset_password")

        user.set_password(password)
        user.forget_password_token = None
        user.forget_password_expiry = None
        user.save()
        messages.success(request, "Password reset successfully!")
        return redirect("sign_in")
    return render(request, "user_side/auth/reset_password.html", {"token": token})

def check(request):
    """
    Comprehensive request inspector view
    Collects all request data and displays it in a terminal-style interface
    """
    
    context = {
        # Basic Request Info
        'method': request.method,
        'path': request.path,
        'full_path': request.get_full_path(),
        'scheme': request.scheme,
        'is_secure': request.is_secure(),
        
        # All HTTP Headers
        'headers': dict(request.headers),
        
        # Cookies
        'cookies': dict(request.COOKIES),
        
        # Query Parameters (GET)
        'get_params': dict(request.GET),
        
        # POST Data
        'post_params': dict(request.POST) if request.method == 'POST' else {},
        
        # Session Information
        'session_key': request.session.session_key if hasattr(request, 'session') else 'N/A',
        
        # User Information
        'user': str(request.user) if hasattr(request, 'user') else 'AnonymousUser',
        'is_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
        
        # Server Meta
        'user_agent': request.META.get('HTTP_USER_AGENT', 'N/A'),
        'remote_addr': request.META.get('REMOTE_ADDR', 'N/A'),
        'remote_host': request.META.get('REMOTE_HOST', 'N/A'),
        'server_name': request.META.get('SERVER_NAME', 'N/A'),
        'server_port': request.META.get('SERVER_PORT', 'N/A'),
        
        # Timestamp
        'timestamp': timezone.now().isoformat(),
    }
    
    # Debug print statements (for your terminal)
    print('=' * 60)
    print('REQUEST DEBUG INFO')
    print('=' * 60)
    print(f'Path: {request.path}')
    print(f"User-Agent: {context['user_agent']}")
    print(f"Accept-Language: {request.headers.get('Accept-Language', 'N/A')}")
    print(f"Cookie: {request.headers.get('Cookie', 'N/A')}")
    print(f"Authorization: {request.headers.get('Authorization', 'N/A')}")
    print(f"session_id: {request.COOKIES.get('sessionid', 'N/A')}")
    print(f"csrf: {request.COOKIES.get('csrftoken', 'N/A')}")
    print(f"host: {request.headers.get('Host', 'N/A')}")
    print('=' * 60)
    
    return render(request, 'user_side/check.html', context)
