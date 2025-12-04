from django.urls import path
from . import views


urlpatterns = [
    # Admin Category management
    path('', views.AdminCategoryListView, name='admin_category'),
    path('category/search/', views.AdminSearchView, name='categories_search'),
    path('category_status/<int:id>/<str:action>/', views.category_status, name='category_status'), 
]