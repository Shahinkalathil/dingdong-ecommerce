from django.shortcuts import render

# Create your views here.
def cart(request):
    return render(request, 'user_side/cart/cart.html')

def checkout(request):
    return render(request, 'user_side/checkout/checkout.html')