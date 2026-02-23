from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import WishlistItem
from products.models import ProductVariant
from offers.utils import get_best_offer_price
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from cart.models import Cart

@login_required
def wishlist(request):
    user = request.user
    wishlist_items = WishlistItem.objects.filter(user=user).select_related(
        "variant__product__brand", "variant__product__category"
    ).prefetch_related("variant__images")
    cart_variant_ids = set()
    try:
        cart = Cart.objects.get(user=user)
        cart_variant_ids = set(cart.items.values_list('variant_id', flat=True))
    except Cart.DoesNotExist:
        pass

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
            'is_in_cart': variant.id in cart_variant_ids, 
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
@require_POST
def toggle_wishlist(request, variant_id):
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_listed=True)

        wishlist_item = WishlistItem.objects.filter(
            user=request.user,
            variant=variant
        ).first()

        if wishlist_item:
            wishlist_item.delete()
            return JsonResponse({
                "success": True,
                "action": "removed",
                "message": "Removed from wishlist."
            })
        else:
            WishlistItem.objects.create(
                user=request.user,
                variant=variant
            )
            return JsonResponse({
                "success": True,
                "action": "added",
                "message": "Added to wishlist."
            })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Something went wrong."
        }, status=400)