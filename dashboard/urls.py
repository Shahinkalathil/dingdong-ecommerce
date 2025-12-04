from django.urls import path
from . import views



urlpatterns = [
    path('',views.DashboardHomeView, name='admin_index'),





    path('brands/', views.admin_brands, name='admin_brands'),
    path('brands/search/', views.brands_search, name='brands_search'),
    path('brands/add/', views.add_brand, name='add_brand'),
    path('brands/edit/<int:brand_id>/', views.edit_brand, name='edit_brand'),
    path('brands/toggle/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'),
    path('brands/delete/<int:brand_id>/', views.delete_brand, name='delete_brand'),

] 
"""
    path('dashboard/sales-reports/', SalesReportListView.as_view(), name='sales_report_list'),
    path('dashboard/sales-reports/export/pdf/', SalesReportPDFView.as_view(), name='sales_report_pdf'),
    path('dashboard/sales-reports/export/excel/', SalesReportExcelView.as_view(), name='sales_report_excel'),
    path('dashboard/analytics/', AnalyticsDashboardView.as_view(), name='analytics'),
"""