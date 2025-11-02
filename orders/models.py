from django.db import models
from products.models import ProductVariant
from uProfile.models import Address
import uuid
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class Order(models.Model):
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Card'),
        ('netbanking', 'Net Banking'),
        ('upi', 'UPI'),
        ('emi', 'EMI'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    order_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)  
    payment_status = models.CharField(max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],default='pending'
    )
    is_paid = models.BooleanField(default=False)
    
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Generate order number if it doesn't exist
        if not self.order_number:
            year = datetime.now().year
            unique_id = str(uuid.uuid4().int)[:6]
            self.order_number = f"DNG-{year}-{unique_id}"
        
        # IMPORTANT: Only set payment status on creation, not on every save
        # This allows admin updates to change payment status when delivered
        if self._state.adding and self.payment_method == 'cod':
            self.payment_status = 'pending'
            self.is_paid = False
        
        # Automatically mark as paid when delivered
        if self.order_status == 'delivered' and self.payment_status != 'paid':
            self.payment_status = 'paid'
            self.is_paid = True
        
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    product_name = models.CharField(max_length=255)
    color_name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.product_name} - Qty: {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)


class OrderAddress(models.Model):
    """
    Separate address snapshot for each order
    """
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    flat_house = models.CharField(max_length=255)
    area_street = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    town_city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_address')

    def __str__(self):
        return f"{self.order.order_number} - {self.full_name}"