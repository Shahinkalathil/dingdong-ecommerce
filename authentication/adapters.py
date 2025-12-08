from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from allauth.core.exceptions import ImmediateHttpResponse  
from django.shortcuts import redirect
from django.contrib import messages

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Connect social account to existing user if email matches
        """
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('email', '').lower()
        
        if not email:
            return
        
        try:
            user = User.objects.get(email=email)
            
            if not user.is_active:
                messages.error(request, 'Your account has been blocked. Contact support.')
                raise ImmediateHttpResponse(redirect('sign_in'))
            
            sociallogin.connect(request, user)
            
        except User.DoesNotExist:
            pass

    def populate_user(self, request, sociallogin, data):
        """
        Populate user data from Google
        """
        user = super().populate_user(request, sociallogin, data)
        
        extra_data = sociallogin.account.extra_data
        email = data.get('email', '').lower()
        
        user.username = email
        
        if not user.fullname:
            user.fullname = extra_data.get('name', '')
            if not user.fullname and user.first_name:
                user.fullname = f"{user.first_name} {user.last_name}".strip()
        
        user.email = email
        user.is_active = True
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after social login
        """
        user = super().save_user(request, sociallogin, form)
        
        if user.username != user.email:
            user.username = user.email
            user.save()
        return user