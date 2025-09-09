from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from django.utils import timezone
from decouple import config


# Create your models here.
class CustomUser(AbstractUser):
    phone = models.CharField(max_length=50, null=True, blank=True)
    fullname = models.CharField(max_length=100)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(null=True, blank=True, default=datetime.datetime.now)
    forget_password_token = models.CharField(max_length=100, null=True, blank=True)
    forget_password_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email if self.email else self.username
    

