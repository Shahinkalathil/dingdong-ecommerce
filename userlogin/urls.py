from django.urls import path
from . import views

urlpatterns = [
    path('sign-up', views.sign_up, name='sign_up'),
    path('otp', views.otp, name='otp'),
    path('resend-otp', views.resend_otp , name='resend_otp'),
    path('sign-in', views.sign_in , name='sign_in'),
    path('forgot-email-check', views.forgot_email_check, name='forgot_email_check'),
    path('reset-password', views.reset_password, name='reset_password'),
]