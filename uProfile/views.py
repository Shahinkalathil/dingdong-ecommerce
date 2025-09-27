from django.shortcuts import render

# Create your views here.
def overview(request):
    context = {
        "show_sidebar": True,  
    }
    return render(request, 'user_side/profile/overview.html', context)

def edit_profile(request):
    context = {
        "show_sidebar": False,  
    }
    return render(request, 'user_side/profile/edit_profile.html', context)

def add_address(request):
    return render(request, 'user_side/profile/add_address.html')

def edit_address(request):
    return render(request, 'user_side/profile/edit_address.html')


def order(request):
    return render(request, 'user_side/profile/order.html')


def order_detail(request):
    return render(request, 'user_side/profile/order_detail.html')
