from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class Address(models.Model):
    COUNTRY_CHOICES = [
        ('India', 'India'),
        ('United States', 'United States'),
        ('United Kingdom', 'United Kingdom'),
        ('Canada', 'Canada'),
        ('Australia', 'Australia'),
    ]
    
    STATE_CHOICES = [
        ('Kerala', 'Kerala'),
        ('Karnataka', 'Karnataka'),
        ('Tamil Nadu', 'Tamil Nadu'),
        ('Maharashtra', 'Maharashtra'),
        ('Delhi', 'Delhi'),
        ('Gujarat', 'Gujarat'),
        ('Rajasthan', 'Rajasthan'),
        ('West Bengal', 'West Bengal'),
    ]
    
    ADDRESS_TYPE_CHOICES = [
        ('Home', '🏠 Home'),
        ('Work', '🏢 Work'),
        ('Other', '📍 Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    country = models.CharField(max_length=50, choices=COUNTRY_CHOICES, default='India')
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    pincode = models.CharField(max_length=10)
    area_street = models.CharField(max_length=255, verbose_name="Area, Street, Sector, Village")
    flat_house = models.CharField(max_length=255, verbose_name="Flat, House no., Building, Company, Apartment")
    landmark = models.CharField(max_length=100, blank=True, null=True)
    town_city = models.CharField(max_length=100)
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='Home')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.address_type} ({self.town_city})"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        else:
            if not self.pk and not Address.objects.filter(user=self.user).exists():
                self.is_default = True
            elif self.pk and Address.objects.filter(user=self.user, is_default=True).count() == 1:
                existing_default = Address.objects.filter(user=self.user, is_default=True).first()
                if existing_default and existing_default.pk == self.pk:
                    if Address.objects.filter(user=self.user).count() == 1:
                        self.is_default = True
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        If deleting a default address and other addresses exist,
        make the most recent address the new default
        """
        is_default_being_deleted = self.is_default
        user = self.user
        
        super().delete(*args, **kwargs)
        if is_default_being_deleted:
            remaining_addresses = Address.objects.filter(user=user)
            if remaining_addresses.exists():
                new_default = remaining_addresses.first()
                new_default.is_default = True
                new_default.save()
    
    def get_full_address(self):
        """Returns the complete formatted address"""
        address_parts = [
            self.flat_house,
            self.area_street,
            self.landmark if self.landmark else '',
            self.town_city,
            self.state,
            self.pincode,
            self.country
        ]
        return ', '.join(filter(None, address_parts))