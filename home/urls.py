from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView, name='home'),
    path('Repair-and-Service', views.RepairServiceView, name="Repair_and_Service"),
   
    path('brands/', views.brands, name='brands_list'),
    path('categories', views.categories, name='categories'),
    
]