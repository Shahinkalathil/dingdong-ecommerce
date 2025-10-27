# products/utils.py
from .models import Product
def get_all_listed_products():
    """
    Return all listed products with their first variant and first image preloaded.
    """
    products = (
        Product.objects
        .filter(is_listed=True, category__is_listed=True, brand__is_listed=True)
        .prefetch_related('variants__images', 'variants')
        .select_related('category', 'brand')
    )

    for product in products:
        product.first_variant = product.variants.first()
        if product.first_variant:
            product.first_image = product.first_variant.images.first()
        else:
            product.first_image = None

    return products
