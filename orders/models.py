from django.db import models
from products.models import ProductVariant
from profiles.models import Address
import uuid
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class Order(models.Model):
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('wallet', 'Wallet'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('returned_checking', 'Returned_Checking'),

    ]
    PAYSTATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    coupon_code = models.CharField(max_length=20, blank=True, null=True) 
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    order_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)  
    payment_status = models.CharField(max_length=20, choices=PAYSTATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False) 
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            year = datetime.now().year
            unique_id = str(uuid.uuid4().int)[:6]
            self.order_number = f"DNG-{year}-{unique_id}"
        
        if self._state.adding and self.payment_method == 'cod':
            self.payment_status = 'pending'
            self.is_paid = False
        
        if self.order_status == 'delivered' and self.payment_status != 'paid':
            self.payment_status = 'paid'
            self.is_paid = True
        
        super().save(*args, **kwargs)

    @property
    def has_cancelled_or_returned_items(self):
        """Check if order has ANY cancelled or returned items"""
        return self.items.filter(
            item_status__in=['cancelled', 'returned']
        ).exists()


class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=255)
    color_name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    item_status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='active')
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    is_returned = models.BooleanField(default=False)
    returned_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.product_name} - Qty: {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        
        # Update item_status based on cancellation/return flags
        if self.is_cancelled:
            self.item_status = 'cancelled'
        elif self.is_returned:
            self.item_status = 'returned'
        else:
            self.item_status = 'active'
            
        super().save(*args, **kwargs)


class OrderAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_address')
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    flat_house = models.CharField(max_length=255)
    area_street = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    town_city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.order.order_number} - {self.full_name}"


class OrderReturn(models.Model):
    RETURN_REASON_CHOICES = [
        ('product_damaged', 'Product Damaged'),
        ('wrong_product', 'Wrong Product Delivered'),
        ('defective', 'Defective/Not Working'),
        ('quality_issue', 'Quality Not as Expected'),
        ('size_issue', 'Size/Fit Issue'),
        ('changed_mind', 'Changed My Mind'),
        ('better_price', 'Found Better Price'),
        ('other', 'Other'),
    ]
    
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='return_request')
    return_reason = models.CharField(max_length=50, choices=RETURN_REASON_CHOICES)
    description = models.TextField(max_length=500, blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Return - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.refund_amount:
            self.refund_amount = self.order.total_amount
        super().save(*args, **kwargs)


class OrderItemReturn(models.Model):
    """Model for individual item returns"""
    RETURN_REASON_CHOICES = [
        ('product_damaged', 'Product Damaged'),
        ('wrong_product', 'Wrong Product Delivered'),
        ('defective', 'Defective/Not Working'),
        ('quality_issue', 'Quality Not as Expected'),
        ('size_issue', 'Size/Fit Issue'),
        ('changed_mind', 'Changed My Mind'),
        ('better_price', 'Found Better Price'),
        ('other', 'Other'),
    ]
    
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='return_request')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='item_returns')
    return_reason = models.CharField(max_length=50, choices=RETURN_REASON_CHOICES)
    description = models.TextField(max_length=500, blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Item Return - {self.order_item.product_name}"
    
    def save(self, *args, **kwargs):
        if not self.refund_amount:
            self.refund_amount = self.order_item.subtotal
        super().save(*args, **kwargs)