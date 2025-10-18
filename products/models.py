from django.db import models

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_listed = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# Model for Brands
class Brand(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_listed = models.BooleanField(default=True)

    def __str__(self):
        return self.name



# Product Model
class Product(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    is_listed = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# Product Variant Model 
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color_name = models.CharField(max_length=30)  
    color_code = models.CharField(max_length=7, default="#000000")
    stock = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_listed = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.color_name}"
    
# Product Image Model 
class ProductImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_variants/")

    def __str__(self):
        return f"Image for {self.variant}"