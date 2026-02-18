from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from orders.models import Order, OrderItem
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
import json
from django.template.loader import render_to_string
from django.http import HttpResponse
import calendar
from weasyprint import HTML

User = get_user_model()
ACTIVE_STATUSES = ['delivered', 'confirmed', 'shipped', 'out_for_delivery']

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def DashboardHomeView(request):
    today = timezone.now().date()
    current_year = today.year

    today_orders_qs = Order.objects.filter(
        created_at__date=today,
        order_status__in=ACTIVE_STATUSES,
    )
    today_stats = today_orders_qs.aggregate(
        total_amount=Sum("total_amount"),
        total_count=Count("id"),
    )

    MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    monthly_sales = []
    for month in range(1, 13):
        result = Order.objects.filter(
            created_at__year=current_year,
            created_at__month=month,
            order_status__in=ACTIVE_STATUSES,
        ).aggregate(total=Sum("total_amount"))
        monthly_sales.append({
            "month": MONTH_NAMES[month - 1],
            "amount": float(result["total"] or 0),
        })

    status_qs = Order.objects.values("order_status").annotate(count=Count("id"))
    status_map = {row["order_status"]: row["count"] for row in status_qs}
    total_orders = sum(status_map.values()) or 1

    order_status_data = [
        {
            "label": "Delivered", "count": status_map.get("delivered", 0),
            "percent": round(status_map.get("delivered", 0) / total_orders * 100), "color": "#1e40af"
        },
        {
            "label": "Confirmed", "count": status_map.get("confirmed", 0),
            "percent": round(status_map.get("confirmed", 0) / total_orders * 100), "color": "#059669"
        },
        {
            "label": "Shipped", "count": status_map.get("shipped", 0),
            "percent": round(status_map.get("shipped", 0) / total_orders * 100), "color": "#7c3aed"
        },
        {
            "label": "Out for Delivery", "count": status_map.get("out_for_delivery", 0),
            "percent": round(status_map.get("out_for_delivery", 0) / total_orders * 100), "color": "#d97706"
        },
        {
            "label": "Pending", "count": status_map.get("pending", 0),
            "percent": round(status_map.get("pending", 0) / total_orders * 100), "color": "#6b7280"
        },
        {
            "label": "Cancelled", "count": status_map.get("cancelled", 0),
            "percent": round(status_map.get("cancelled", 0) / total_orders * 100), "color": "#dc2626"
        },
        {
            "label": "Returned", "count": status_map.get("returned", 0),
            "percent": round(status_map.get("returned", 0) / total_orders * 100), "color": "#f59e0b"
        },
    ]

    context = {
        "today_sales": today_stats["total_amount"] or Decimal("0.00"),
        "today_orders": today_stats["total_count"] or 0,
        "current_year": current_year,
        "monthly_sales_data": json.dumps(monthly_sales),
        "order_status_data": json.dumps(order_status_data),
        "total_orders": total_orders,
        "current_super": request.user,
    }

    return render(request, "admin_panel/index.html", context)

def _get_date_range(report_type, start_date_str, end_date_str, today):
    orders = Order.objects.filter(order_status__in=ACTIVE_STATUSES)

    if report_type == 'daily':
        orders = orders.filter(created_at__date=today)
        period_label = f"Daily Report – {today.strftime('%B %d, %Y')}"
        chart_labels = [f"{h:02d}:00" for h in range(24)]
        chart_amounts = [float(orders.filter(created_at__hour=h).aggregate(t=Sum('total_amount'))['t'] or 0) for h in range(24)]

    elif report_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        orders = orders.filter(created_at__date__range=[week_start, week_end])
        period_label = f"Weekly Report – {week_start.strftime('%b %d')} to {week_end.strftime('%b %d, %Y')}"
        chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        chart_amounts = [float(orders.filter(created_at__date=week_start + timedelta(days=i)).aggregate(t=Sum('total_amount'))['t'] or 0) for i in range(7)]

    elif report_type == 'monthly':
        orders = orders.filter(created_at__year=today.year, created_at__month=today.month)
        period_label = f"Monthly Report – {today.strftime('%B %Y')}"
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        chart_labels = [str(d) for d in range(1, days_in_month + 1)]
        chart_amounts = [float(orders.filter(created_at__day=d).aggregate(t=Sum('total_amount'))['t'] or 0) for d in range(1, days_in_month + 1)]

    elif report_type == 'yearly':
        orders = orders.filter(created_at__year=today.year)
        period_label = f"Yearly Report – {today.year}"
        MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        chart_labels = MONTHS
        chart_amounts = [float(orders.filter(created_at__month=m).aggregate(t=Sum('total_amount'))['t'] or 0) for m in range(1, 13)]

    elif report_type == 'custom' and start_date_str and end_date_str:
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__range=[start, end])
            period_label = f"Custom – {start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')}"
            delta = (end - start).days + 1
            chart_labels = [(start + timedelta(days=i)).strftime('%d %b') for i in range(delta)]
            chart_amounts = [float(orders.filter(created_at__date=start + timedelta(days=i)).aggregate(t=Sum('total_amount'))['t'] or 0) for i in range(delta)]
        except ValueError:
            period_label = "Custom Report"
            chart_labels, chart_amounts = [], []
            
    else:
        period_label = "All Time Report"
        MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        chart_labels = MONTHS
        chart_amounts = [float(orders.filter(created_at__month=m).aggregate(t=Sum('total_amount'))['t'] or 0) for m in range(1, 13)]

    return orders, period_label, json.dumps({'labels': chart_labels, 'amounts': chart_amounts})


def _best_sellers(orders):
    item_qs = OrderItem.objects.filter(order__in=orders, item_status='active')
    
    top_products = list(item_qs.values('product_name').annotate(
        total_qty=Sum('quantity'), total_rev=Sum('subtotal')).order_by('-total_qty')[:10])
    
    top_categories = list(item_qs.filter(variant__product__category__isnull=False).values(
        name=F('variant__product__category__name')).annotate(
        total_qty=Sum('quantity'), total_rev=Sum('subtotal')).order_by('-total_qty')[:10])
    
    top_brands = list(item_qs.filter(variant__product__brand__isnull=False).values(
        name=F('variant__product__brand__name')).annotate(
        total_qty=Sum('quantity'), total_rev=Sum('subtotal')).order_by('-total_qty')[:10])

    return top_products, top_categories, top_brands


def _payment_breakdown(orders):
    rows = orders.values('payment_method').annotate(
        total=Sum('total_amount'), count=Count('id')).order_by('-total')
    
    METHOD_LABELS = {'cod': 'Cash on Delivery', 'online': 'Online', 'wallet': 'Wallet'}
    return [{'method': METHOD_LABELS.get(r['payment_method'], r['payment_method'].upper()),
             'total': r['total'] or Decimal('0'), 'count': r['count']} for r in rows]


def _date_rows(orders, report_type, start_date_str, end_date_str, today):
    rows = []

    if report_type == 'daily':
        for h in range(24):
            agg = orders.filter(created_at__hour=h).aggregate(
                total=Sum('total_amount'), discount=Sum('discount_amount'),
                coupon=Sum('coupon_discount'), count=Count('id'))
            if agg['count']:
                rows.append({'date': f"{today.strftime('%Y-%m-%d')} {h:02d}:00", 'count': agg['count'],
                           'total': agg['total'] or Decimal('0'),
                           'discount': (agg['discount'] or Decimal('0')) + (agg['coupon'] or Decimal('0'))})

    elif report_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        for i in range(7):
            day = week_start + timedelta(days=i)
            agg = orders.filter(created_at__date=day).aggregate(
                total=Sum('total_amount'), discount=Sum('discount_amount'),
                coupon=Sum('coupon_discount'), count=Count('id'))
            rows.append({'date': day.strftime('%Y-%m-%d'), 'count': agg['count'] or 0,
                       'total': agg['total'] or Decimal('0'),
                       'discount': (agg['discount'] or Decimal('0')) + (agg['coupon'] or Decimal('0'))})

    elif report_type == 'monthly':
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        for d in range(1, days_in_month + 1):
            agg = orders.filter(created_at__day=d).aggregate(
                total=Sum('total_amount'), discount=Sum('discount_amount'),
                coupon=Sum('coupon_discount'), count=Count('id'))
            if agg['count']:
                rows.append({'date': f"{today.year}-{today.month:02d}-{d:02d}", 'count': agg['count'],
                           'total': agg['total'] or Decimal('0'),
                           'discount': (agg['discount'] or Decimal('0')) + (agg['coupon'] or Decimal('0'))})

    elif report_type == 'yearly':
        MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for m in range(1, 13):
            agg = orders.filter(created_at__month=m).aggregate(
                total=Sum('total_amount'), discount=Sum('discount_amount'),
                coupon=Sum('coupon_discount'), count=Count('id'))
            if agg['count']:
                rows.append({'date': f"{today.year} {MONTHS[m-1]}", 'count': agg['count'],
                           'total': agg['total'] or Decimal('0'),
                           'discount': (agg['discount'] or Decimal('0')) + (agg['coupon'] or Decimal('0'))})

    elif report_type == 'custom' and start_date_str and end_date_str:
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            delta = (end - start).days + 1
            for i in range(delta):
                day = start + timedelta(days=i)
                agg = orders.filter(created_at__date=day).aggregate(
                    total=Sum('total_amount'), discount=Sum('discount_amount'),
                    coupon=Sum('coupon_discount'), count=Count('id'))
                if agg['count']:
                    rows.append({'date': day.strftime('%Y-%m-%d'), 'count': agg['count'],
                               'total': agg['total'] or Decimal('0'),
                               'discount': (agg['discount'] or Decimal('0')) + (agg['coupon'] or Decimal('0'))})
        except ValueError:
            pass

    else:
        daily = orders.annotate(day=TruncDate('created_at')).values('day').annotate(
            total=Sum('total_amount'), discount=Sum('discount_amount'),
            coupon=Sum('coupon_discount'), count=Count('id')).order_by('day')
        for r in daily:
            rows.append({'date': r['day'].strftime('%Y-%m-%d'), 'count': r['count'],
                       'total': r['total'] or Decimal('0'),
                       'discount': (r['discount'] or Decimal('0')) + (r['coupon'] or Decimal('0'))})

    return rows

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def sales_report_view(request):
    report_type = request.GET.get('report_type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    today = timezone.now().date()

    orders, period_label, chart_data = _get_date_range(report_type, start_date, end_date, today)

    totals = orders.aggregate(
        total_count=Count('id'), total_amount=Sum('total_amount'),
        total_discount=Sum('discount_amount'), total_coupon=Sum('coupon_discount'))

    top_products, top_categories, top_brands = _best_sellers(orders)

    order_rows = []
    for order in orders.select_related('user').prefetch_related('items').order_by('-created_at'):
        active_items = order.items.filter(item_status='active')
        items_summary = ', '.join(f"{i.product_name} ×{i.quantity}" for i in active_items)
        order_rows.append({
            'order_number': order.order_number,
            'customer': order.user.get_full_name() or order.user.username,
            'items': items_summary,
            'amount': order.total_amount,
            'payment': order.get_payment_method_display(),
            'status': order.get_order_status_display(),
            'status_raw': order.order_status,
            'discount': (order.discount_amount or 0) + (order.coupon_discount or 0),
        })

    total_discount = (totals['total_discount'] or Decimal('0')) + (totals['total_coupon'] or Decimal('0'))

    context = {
        'report_type': report_type, 'start_date': start_date, 'end_date': end_date,
        'period_label': period_label, 'total_sales_count': totals['total_count'] or 0,
        'total_order_amount': totals['total_amount'] or Decimal('0'),
        'total_discount': total_discount, 'order_rows': order_rows,
        'chart_data': chart_data, 'top_products': top_products,
        'top_categories': top_categories, 'top_brands': top_brands,
    }
    return render(request, 'admin_panel/sales_report.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(lambda u: u.is_superuser, login_url="admin_login")
def download_sales_pdf(request):
    report_type = request.GET.get('report_type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    today = timezone.now().date()

    orders, period_label, _ = _get_date_range(report_type, start_date, end_date, today)

    totals = orders.aggregate(
        total_count=Count('id'), total_amount=Sum('total_amount'),
        total_discount=Sum('discount_amount'), total_coupon=Sum('coupon_discount'))
    
    total_discount = (totals['total_discount'] or Decimal('0')) + (totals['total_coupon'] or Decimal('0'))

    context = {
        'report_type': report_type,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'total_sales_count': totals['total_count'] or 0,
        'total_order_amount': totals['total_amount'] or Decimal('0'),
        'total_discount': total_discount,
        'payment_breakdown': _payment_breakdown(orders),
        'date_rows': _date_rows(orders, report_type, start_date, end_date, today),
    }

    html_string = render_to_string('admin_panel/sales_report_pdf.html', context, request=request)
    
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"sales_report_{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response