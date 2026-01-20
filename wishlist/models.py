from django.conf import settings
from django.db import models
from products.models import ProductVariant
# Create your models here.

class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_user")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="wishlisted_variants")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "variant")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.variant.product.name} ({self.variant.color_name})"
