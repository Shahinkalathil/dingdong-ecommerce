from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from products.models import ProductVariant

# Cart Model
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user.fullname if self.user.fullname else self.user.username}"
    
    def get_total_price(self):
        """Calculate total price of all items in cart"""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def clear_cart(self):
        """Remove all items from cart"""
        self.items.all().delete()

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} ({self.variant.color_name})"
    
    def get_subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.variant.price * self.quantity
    
    def is_in_stock(self):
        """Check if requested quantity is available in stock"""
        return self.quantity <= self.variant.stock
    
    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'variant']  
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
