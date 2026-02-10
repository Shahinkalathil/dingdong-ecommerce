from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_control
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.db.models import Sum, Count
from orders.models import Order
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
import io
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def DashboardHomeView(request):
    User = get_user_model()
    
    # Get today's date
    today = timezone.now().date()
    
    # Calculate today's sales
    today_orders = Order.objects.filter(
        created_at__date=today,
        order_status__in=['delivered', 'confirmed', 'shipped', 'out_for_delivery']
    )
    
    today_sales = today_orders.aggregate(
        total_amount=Sum('total_amount'),
        total_count=Count('id')
    )
    
    # Get week data for chart
    week_start = today - timedelta(days=today.weekday())
    daily_sales = []
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_orders = Order.objects.filter(
            created_at__date=day,
            order_status__in=['delivered', 'confirmed', 'shipped', 'out_for_delivery']
        ).aggregate(total=Sum('total_amount'))
        
        daily_sales.append({
            'date': day.strftime('%d %b'),
            'amount': float(day_orders['total'] or 0)
        })
    
    # Recent orders for table
    recent_orders = Order.objects.filter(
        order_status__in=['delivered', 'confirmed', 'shipped', 'out_for_delivery']
    ).select_related('user').prefetch_related('items').order_by('-created_at')[:10]
    
    recent_order_details = []
    for order in recent_orders:
        active_items = order.items.filter(item_status='active')
        for item in active_items:
            recent_order_details.append({
                'customer': order.user.get_full_name() or order.user.username,
                'product_name': item.product_name,
                'order_number': order.order_number,
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.subtotal,
            })
            break  # Only show first item for dashboard
    
    superusers = User.objects.filter(is_superuser=True).values("username", "email")
    current_super = request.user
    
    context = {
        "superusers": superusers,
        "current_super": current_super,
        "today_sales": today_sales['total_amount'] or Decimal('0.00'),
        "today_orders": today_sales['total_count'] or 0,
        "daily_sales_data": json.dumps(daily_sales),
        "recent_orders": recent_order_details,
    }
    
    return render(request, "admin_panel/index.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def sales_report_view(request):
    # Get filter parameters
    report_type = request.GET.get('report_type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Base queryset - only delivered and confirmed orders
    orders = Order.objects.filter(
        order_status__in=['delivered', 'confirmed', 'shipped', 'out_for_delivery']
    )
    
    # Apply date filters
    today = timezone.now().date()
    
    if report_type == 'daily':
        orders = orders.filter(created_at__date=today)
        period_label = f"Daily Report - {today.strftime('%B %d, %Y')}"
    elif report_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        orders = orders.filter(created_at__date__range=[week_start, week_end])
        period_label = f"Weekly Report - {week_start.strftime('%b %d')} to {week_end.strftime('%b %d, %Y')}"
    elif report_type == 'monthly':
        orders = orders.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )
        period_label = f"Monthly Report - {today.strftime('%B %Y')}"
    elif report_type == 'yearly':
        orders = orders.filter(created_at__year=today.year)
        period_label = f"Yearly Report - {today.year}"
    elif report_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__range=[start, end])
            period_label = f"Custom Report - {start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')}"
        except ValueError:
            period_label = "Custom Report"
    else:
        # All time
        period_label = "All Time Report"
    
    # Calculate aggregated data
    total_sales = orders.aggregate(
        total_count=Count('id'),
        total_amount=Sum('total_amount'),
        total_discount=Sum('discount_amount'),
        total_coupon_discount=Sum('coupon_discount')
    )
    
    # Get order details with items
    order_details = []
    for order in orders.select_related('user').prefetch_related('items'):
        active_items = order.items.filter(item_status='active')
        
        for item in active_items:
            order_details.append({
                'order_number': order.order_number,
                'date': order.created_at,
                'customer': order.user.get_full_name() or order.user.username,
                'product_name': item.product_name,
                'color': item.color_name,
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.subtotal,
                'payment_method': order.get_payment_method_display(),
                'status': order.get_order_status_display(),
            })
    
    # Calculate totals
    total_order_amount = total_sales['total_amount'] or Decimal('0.00')
    total_discount_amount = (total_sales['total_discount'] or Decimal('0.00')) + (total_sales['total_coupon_discount'] or Decimal('0.00'))
    
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'total_sales_count': total_sales['total_count'] or 0,
        'total_order_amount': total_order_amount,
        'total_discount': total_discount_amount,
        'order_details': order_details,
    }
    
    return render(request, 'admin_panel/sales_report.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="admin_login")
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def download_sales_pdf(request):
    # Get the same filter parameters
    report_type = request.GET.get('report_type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Apply the same filters as the view
    orders = Order.objects.filter(
        order_status__in=['delivered', 'confirmed', 'shipped', 'out_for_delivery']
    )
    
    today = timezone.now().date()
    
    if report_type == 'daily':
        orders = orders.filter(created_at__date=today)
        period_label = f"Daily Report - {today.strftime('%B %d, %Y')}"
    elif report_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        orders = orders.filter(created_at__date__range=[week_start, week_end])
        period_label = f"Weekly Report - {week_start.strftime('%b %d')} to {week_end.strftime('%b %d, %Y')}"
    elif report_type == 'monthly':
        orders = orders.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )
        period_label = f"Monthly Report - {today.strftime('%B %Y')}"
    elif report_type == 'yearly':
        orders = orders.filter(created_at__year=today.year)
        period_label = f"Yearly Report - {today.year}"
    elif report_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__range=[start, end])
            period_label = f"Custom Report - {start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')}"
        except ValueError:
            period_label = "Custom Report"
    else:
        period_label = "All Time Report"
    
    # Calculate totals
    total_sales = orders.aggregate(
        total_count=Count('id'),
        total_amount=Sum('total_amount'),
        total_discount=Sum('discount_amount'),
        total_coupon_discount=Sum('coupon_discount')
    )
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Add title
    title = Paragraph("DINGDONG Sales Report", title_style)
    elements.append(title)
    
    # Add period label
    period = Paragraph(period_label, heading_style)
    elements.append(period)
    elements.append(Spacer(1, 20))
    
    # Summary data
    total_order_amount = total_sales['total_amount'] or Decimal('0.00')
    total_discount_amount = (total_sales['total_discount'] or Decimal('0.00')) + (total_sales['total_coupon_discount'] or Decimal('0.00'))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Sales Count', str(total_sales['total_count'] or 0)],
        ['Total Order Amount', f"${total_order_amount:,.2f}"],
        ['Total Discount', f"${total_discount_amount:,.2f}"],
        ['Net Revenue', f"${(total_order_amount - total_discount_amount):,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Order details
    if orders.exists():
        details_heading = Paragraph("Order Details", heading_style)
        elements.append(details_heading)
        elements.append(Spacer(1, 10))
        
        # Table header
        detail_data = [['Order ID', 'Date', 'Customer', 'Items', 'Amount', 'Discount']]
        
        for order in orders.select_related('user'):
            active_items = order.items.filter(item_status='active')
            item_count = active_items.count()
            
            detail_data.append([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d'),
                order.user.get_full_name() or order.user.username,
                str(item_count),
                f"${order.total_amount:,.2f}",
                f"${(order.discount_amount + order.coupon_discount):,.2f}"
            ])
        
        detail_table = Table(detail_data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ]))
        
        elements.append(detail_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{report_type}_{today.strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    
    return response