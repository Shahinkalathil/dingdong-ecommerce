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

    return final_price, best_discount
