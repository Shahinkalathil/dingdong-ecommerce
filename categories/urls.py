from django.urls import path
from . import views


urlpatterns = [
    # Admin Category management
    path('admin-management/', views.AdminCategoryListView, name='admin_category'),
    path('admin-management/search/', views.AdminSearchView, name='categories_search'),
    path('admin-management/category-status/<int:id>/<str:action>/', views.category_status, name='category_status'), 
]