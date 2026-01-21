from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import WishlistItem
from cart.models import CartItem, Cart
from products.models import ProductImage,ProductVariant
from django.urls import reverse

@login_required
def wishlist(request):
    user = request.user
    try:
        user_cart = Cart.objects.get(user=user)
        cart_variant_ids = CartItem.objects.filter(cart=user_cart).values_list("variant_id", flat=True)
    except Cart.DoesNotExist:
        cart_variant_ids = []
    wishlist_items = WishlistItem.objects.filter(user=user).exclude(variant_id__in=cart_variant_ids).select_related("variant", "variant__product", "variant__product__brand")
    wishlist_data = []
    for item in wishlist_items:
        variant = item.variant
        product = variant.product
        product_image = ProductImage.objects.filter(variant=variant).first()
        price = variant.price
        in_stock = variant.stock > 0
        
        wishlist_data.append({
            'wishlist_item': item,
            'product': product,
            'variant': variant,
            'image': product_image,
            'price': price,
            'in_stock': in_stock,
        })
    
    context = {
        'wishlist_data': wishlist_data,
        'total_items': len(wishlist_data),
    }  
    return render(request, "user_side/wishlist/wishlist.html", context)

@login_required
def remove_from_wishlist(request, variant_id):
    try:
        wishlist_item = WishlistItem.objects.get(user=request.user, variant_id=variant_id)
        product_name = wishlist_item.variant.product.name
        wishlist_item.delete()
        messages.success(request, f'{product_name} removed from your wishlist.')
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found in your wishlist.')
    return redirect('wishlist')
<<<<<<< HEAD
=======

@login_required
def toggle_wishlist(request, variant_id):
    if request.method != 'POST':
        return redirect('products')
    
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_listed=True)
        
        # Check if variant is in cart
        cart = getattr(request.user, 'cart', None)
        if cart and CartItem.objects.filter(cart=cart, variant=variant).exists():
            messages.error(request, "already in your cart..")
            return redirect('product_detail', variant.product.id)
        
        # Toggle wishlist
        wishlist_item = WishlistItem.objects.filter(user=request.user, variant=variant).first()
        
        if wishlist_item:
            wishlist_item.delete()
            messages.success(request, "removed from wishlist.")
        else:
            WishlistItem.objects.create(user=request.user, variant=variant)
            messages.success(request, "added to wishlist!")

    except ProductVariant.DoesNotExist:
        messages.error(request, "Product variant not found.")
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
    
    return redirect('product_detail', variant.product.id)
>>>>>>> 6925381 (feat: whislist button funtionly in the product_listing page complted with error handling)
