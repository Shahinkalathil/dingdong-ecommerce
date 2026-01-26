from datetime import datetime
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from products.models import Brand
from .models import BrandOffer
from django.views.decorators.http import require_POST

def AdminBrandOfferCreateView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand_offer = BrandOffer.objects.filter(brand=brand).first()
    discount = request.POST.get('discount_percentage', '').strip()
    valid_until = request.POST.get('valid_until', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    try:
        valid_until_date = timezone.make_aware(
            datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
        )

        if brand_offer:
            brand_offer.discount_percentage = discount
            brand_offer.valid_until = valid_until_date
            brand_offer.is_active = is_active
            brand_offer.updated_at = timezone.now()
            brand_offer.save()
        else:
            BrandOffer.objects.create(
                brand=brand,
                discount_percentage=discount,
                valid_until=valid_until_date,
                is_active=is_active
            ) 
    except Exception as e:
        pass
    return redirect('edit_brand', brand_id=brand_id)

@require_POST  
def AdminBrandOfferDeleteView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
        brand_offer.delete()
    except BrandOffer.DoesNotExist:
        pass
    return redirect('edit_brand', brand_id=brand_id)

@require_POST  
def AdminBrandBlockView(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    try:
        brand_offer = BrandOffer.objects.get(brand=brand)
        brand_offer.is_active = not brand_offer.is_active
        brand_offer.save()  
    except BrandOffer.DoesNotExist:
        pass
    return redirect('edit_brand', brand_id=brand_id)