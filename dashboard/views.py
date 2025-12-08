from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_control
from django.contrib.auth import get_user_model


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def DashboardHomeView(request):
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user  
    context = {
        "superusers": superusers,        
        "current_super": current_super,   
    }
    return render(request, "admin_panel/index.html", context)


"""
sales_report_view

download_sales_pdf

download_sales_excel

analytics_view
"""
