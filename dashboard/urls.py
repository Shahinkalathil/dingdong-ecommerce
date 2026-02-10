from django.urls import path
from . import views



urlpatterns = [
    path('', views.DashboardHomeView, name='admin_index'),
    path('sales-report/', views.sales_report_view, name='sales_report'),
    path('sales-report/download-pdf/', views.download_sales_pdf, name='download_sales_pdf'),
]

