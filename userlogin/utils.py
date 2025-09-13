from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import redirect

def send_otp_email(email, otp):
    subject = "Your OTP for Account Verification"
    message = f"Your OTP is {otp}. It will expire in 1 minute."
    email_from = None   # uses DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)
    return True

def send_forget_password_mail(email, token, request):
    reset_link = request.build_absolute_uri(
        reverse("reset_password") + f"?token={token}"
    )
    subject = "Reset Your Password"
    message = f"Click the link below to reset your password:\n\n{reset_link}\n\nThis link is valid for 15 minutes."
    email_from = None
    recipient_list = [email]

    send_mail(subject, message, email_from, recipient_list)
    return True


def redirect_authenticated(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper