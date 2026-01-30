from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from products.models import Brand, Product
from django.utils import timezone


# Create your models here.
class BrandOffer(models.Model):
    brand = models.OneToOneField(Brand, on_delete=models.CASCADE, related_name='brand_offer')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(1), MaxValueValidator(100)],)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.brand.name} - {self.discount_percentage}%"
    
class ProductOffer(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='product_offer')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(1), MaxValueValidator(100)],)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}%"
    
    def is_valid(self):
        now = timezone.now()
        return self.is_active and (
            self.valid_until is None or self.valid_until >= now
        )