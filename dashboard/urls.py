from django.urls import path
from . import views



urlpatterns = [
    path('',views.DashboardHomeView, name='admin_index'),

] 
"""
    path('dashboard/sales-reports/', SalesReportListView.as_view(), name='sales_report_list'),
    path('dashboard/sales-reports/export/pdf/', SalesReportPDFView.as_view(), name='sales_report_pdf'),
    path('dashboard/sales-reports/export/excel/', SalesReportExcelView.as_view(), name='sales_report_excel'),
    path('dashboard/analytics/', AnalyticsDashboardView.as_view(), name='analytics'),
"""