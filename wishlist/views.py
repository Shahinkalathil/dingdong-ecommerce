from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import WishlistItem
from cart.models import CartItem, Cart
from products.models import ProductImage, ProductVariant
from offers.utils import get_best_offer_price


@login_required
def wishlist(request):
    """
    Display user's wishlist
    Excludes items already in cart
    """
    user = request.user
    try:
        user_cart = Cart.objects.get(user=user)
        cart_variant_ids = CartItem.objects.filter(cart=user_cart).values_list("variant_id", flat=True)
    except Cart.DoesNotExist:
        cart_variant_ids = []
    wishlist_items = WishlistItem.objects.filter(
        user=user
    ).exclude(
        variant_id__in=cart_variant_ids
    ).select_related(
        "variant__product__brand",
        "variant__product__category"
    ).prefetch_related(
        "variant__images"
    )
    
    wishlist_data = []
    for item in wishlist_items:
        variant = item.variant
        product = variant.product
        
        product_image = variant.images.first()

        original_price = variant.price
        final_price, discount_percentage = get_best_offer_price(product, original_price)

        in_stock = variant.stock > 0
        
        wishlist_data.append({
            'wishlist_item': item,
            'product': product,
            'variant': variant,
            'image': product_image,
            'original_price': original_price,
            'price': final_price,
            'discount_percentage': discount_percentage,
            'in_stock': in_stock,
        })
    
    context = {
        'wishlist_data': wishlist_data,
        'total_items': len(wishlist_data),
    }
    
    return render(request, "user_side/wishlist/wishlist.html", context)


@login_required
def remove_from_wishlist(request, variant_id):
    """
    Remove item from wishlist
    """
    try:
        wishlist_item = WishlistItem.objects.get(user=request.user, variant_id=variant_id)
        wishlist_item.delete()
        messages.success(request, 'Removed from wishlist.')
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found.')
    
    return redirect('wishlist')


@login_required
def toggle_wishlist(request, variant_id):
    """
    Toggle wishlist for a specific product variant
    Redirects back to the same variant detail page
    """
    if request.method != 'POST':
        return redirect('products')
    
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_listed=True)
        
        if not variant.product.is_listed or not variant.product.category.is_listed or not variant.product.brand.is_listed:
            messages.error(request, "Product not available.")
            return redirect('products')
        
        try:
            cart = Cart.objects.get(user=request.user)
            if CartItem.objects.filter(cart=cart, variant=variant).exists():
                messages.info(request, "Already in cart.")
                return redirect('product_detail', variant_id=variant_id)
        except Cart.DoesNotExist:
            pass

        wishlist_item = WishlistItem.objects.filter(user=request.user, variant=variant).first()
        
        if wishlist_item:
            wishlist_item.delete()
            messages.success(request, "Removed from wishlist.")
        else:
            WishlistItem.objects.create(user=request.user, variant=variant)
            messages.success(request, "Added to wishlist.")
        return redirect('product_detail', variant_id=variant_id)

    except ProductVariant.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect('products')
    except Exception as e:
        print(f"Error in toggle_wishlist: {e}")
        messages.error(request, "Something went wrong.")
        return redirect('products')