# offers/utils.py
from django.utils import timezone
from decimal import Decimal

def get_best_offer_price(product, base_price):
    best_discount = Decimal("0")

    # Product offer
    product_offer = getattr(product, "product_offer", None)
    if product_offer and product_offer.is_valid():
        best_discount = product_offer.discount_percentage

    # Brand offer
    brand_offer = getattr(product.brand, "brand_offer", None)
    if brand_offer and brand_offer.is_active:
        now = timezone.now()
        if brand_offer.valid_until is None or brand_offer.valid_until >= now:
            if brand_offer.discount_percentage > best_discount:
                best_discount = brand_offer.discount_percentage

    discount_amount = (base_price * best_discount) / Decimal("100")
    final_price = base_price - discount_amount

    return final_price, best_discount, 

def get_offer_details(product, base_price):
    """
    Wrapper function to get offer details including offer type.
    Uses the existing get_best_offer_price from offers.utils
    """
    # Get the discounted price and discount percentage
    final_price, discount_percentage = get_best_offer_price(product, base_price)
    
    # Determine offer type
    offer_type = None
    if discount_percentage > 0:
        # Check which offer is applied
        product_offer = getattr(product, "product_offer", None)
        if product_offer and product_offer.is_valid():
            if product_offer.discount_percentage == discount_percentage:
                offer_type = 'product'
        
        # If not product offer, check brand offer
        if offer_type is None:
            brand_offer = getattr(product.brand, "brand_offer", None)
            if brand_offer and brand_offer.is_active:
                now = timezone.now()
                if brand_offer.valid_until is None or brand_offer.valid_until >= now:
                    if brand_offer.discount_percentage == discount_percentage:
                        offer_type = 'brand'
    
    return final_price, discount_percentage, offer_type