from django.db.models.functions import ExtractHour
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, F, FloatField, ExpressionWrapper
from django.utils.timezone import localtime
from .models import *

from datetime import datetime, timedelta, time

import json

def dashboard(request):
    now = localtime().now()
    today = now.date()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    yesterday_midnight = today_midnight - timedelta(days=1)
    yesterday_current_time = now - timedelta(days=1)

    #x-report
    yesterday_sales = Sale.objects.filter(created_at__range=(yesterday_midnight, yesterday_current_time))
    today_sales = Sale.objects.filter(created_at__range=(today_midnight, now))
    yesterday_sales_total = yesterday_sales.aggregate(Sum("total"))["total__sum"] or 0
    today_sales_total = today_sales.aggregate(Sum("total"))["total__sum"] or 0
    if yesterday_sales_total!=0:
        percentage_change = ((today_sales_total-yesterday_sales_total)/yesterday_sales_total)*100
    elif today_sales_total>0:
        percentage_change = 100
    else:
        percentage_change=0
    difference = today_sales.count()-yesterday_sales.count()

    average_basket = today_sales.aggregate(Avg("total"))["total__avg"] or 0
    average_basket_yesterday = yesterday_sales.aggregate(Avg("total"))["total__avg"] or 0
    if average_basket_yesterday!=0:
        avg_percent_change = ((average_basket-average_basket_yesterday
                           )/average_basket_yesterday)*100
    elif average_basket>0:
        avg_percent_change = 100
    else:
        avg_percent_change=0

    items_sold = SaleItem.objects.filter(sale__created_at__range=(today_midnight, now)
                                         ).aggregate(Sum("qty"))["qty__sum"] or 0
    items_sold_yesterday = SaleItem.objects.filter(sale__created_at__range=(yesterday_midnight, yesterday_current_time)
                                                   ).aggregate(Sum("qty"))["qty__sum"] or 0
    if items_sold_yesterday!=0:
        items_sold_change = ((items_sold-items_sold_yesterday)/items_sold_yesterday)*100
    elif items_sold>0:
        items_sold_change = 100
    else:
        items_sold_change=0

    #sales by hour
    hour_totals = (today_sales.annotate(hour=ExtractHour('created_at'))
                     .values('hour')
                     .annotate(total=Sum('total'))
                     .order_by('hour'))
    sales_by_hour = []
    hour_totals = {row['hour']: int(row['total']) for row in hour_totals}
    for hour in range(0, 24):
        total = hour_totals.get(hour, 0)
        sales_by_hour.append({
            "hour": hour,
            "total": total,
        })

    #top sellers
    saleitem = (SaleItem.objects.filter(sale__created_at__range=(today_midnight, now))
                .values("product__name")
                .annotate(total_price=Sum("price"))
                ).order_by('-total_price')
    top_sellers = []
    for item in saleitem:
        top_sellers.append({
            "name": item["product__name"],
            "total": item["total_price"],
        })

    #REPORTS
    #yesterday
    yesterday_all_sales = Sale.objects.filter(created_at__date=yesterday).aggregate(Sum("total"))["total__sum"] or 0
    yesterday_profit = SaleItem.objects.filter(sale__created_at__date=yesterday).aggregate(Sum("profit"))["profit__sum"] or 0
    yesterday_expenses = Expense.objects.filter(created_at__date=yesterday).aggregate(Sum("expense"))["expense__sum"] or 0

    #7 days
    days_7_before = today - timedelta(days=7)
    days_7_all_sales = Sale.objects.filter(created_at__date__range=(days_7_before, today)).aggregate(Sum("total"))["total__sum"] or 0
    days_7_profit = SaleItem.objects.filter(sale__created_at__date__range=(days_7_before, today)).aggregate(Sum("profit"))["profit__sum"] or 0
    days_7_expenses = Expense.objects.filter(created_at__date__range=(days_7_before, today)).aggregate(Sum("expense"))["expense__sum"] or 0

    #this month
    month = today.replace(day=1)
    month_all_sales = Sale.objects.filter(created_at__date__range=(month, today)).aggregate(Sum("total"))["total__sum"] or 0
    month_profit = SaleItem.objects.filter(sale__created_at__date__range=(month, today)).aggregate(Sum("profit"))["profit__sum"] or 0
    month_expenses = Expense.objects.filter(created_at__date__range=(month, today)).aggregate(Sum("expense"))["expense__sum"] or 0



    context = {
        "today_sales": today_sales,
        "yesterday_sales": yesterday_sales,
        "today_sales_total": today_sales_total,
        "yesterday_sales_total": yesterday_sales_total,
        "percentage_change": percentage_change,
        "difference": difference,
        "localtime": now,
        "average_basket": average_basket,
        "items_sold": items_sold,
        "avg_percent_change": avg_percent_change,
        "items_sold_change": items_sold_change,
        "sales_by_hour": sales_by_hour,
        "top_sellers": top_sellers[:5],
        "yesterday_all_sales": yesterday_all_sales,
        "yesterday_profit": yesterday_profit,
        "yesterday_expenses": yesterday_expenses,
        "days_7_all_sales": days_7_all_sales,
        "days_7_profit": days_7_profit,
        "days_7_expenses": days_7_expenses,
        "month_all_sales": month_all_sales,
        "month_profit": month_profit,
        "month_expenses": month_expenses,
        "month_name": now.strftime("%B"),
    }
    return render(request, "dashboard.html", context)

def point_of_sale(request):
    last_sale = Sale.objects.last()
    context = {
        "products": Product.objects.all(),
        "current_sale_id": (last_sale.id + 1) if last_sale else 1
    }
    if request.method == "POST":
        products = json.loads(request.body)['items']
        sale = Sale.objects.create(created_at=localtime(), total=0)
        for key, item in products.items():
            product = Product.objects.get(id=key)
            qty = item.get('qty')
            if not qty:
                qty = item.get('weight')
            price = item.get('price')
            sale_item = SaleItem.objects.create(product=product, sale=sale, price=qty*price, qty=float(qty), profit=float(product.vendor_cost*qty))
            sale.total+=(qty*price)
        sale.save()
        return JsonResponse({"status": "ok", "sale_id":last_sale.id, "next_sale_id": last_sale.id+1, "sale_total":sale.total})


        
    return render(request, "pos.html", context)


def products_list(request):
    context = {
        "products": Product.objects.all()
    }
    return render(request, "products.html", context)

def product_add(request):
    if request.method == "POST":
        print(request.POST.get("barcode"))
        name = request.POST.get("name")
        barcode = request.POST.get("barcode")
        sales_price = request.POST.get("price")
        vendor_cost = request.POST.get("vendor_cost")
        qty = request.POST.get("qty")
        weight_based = request.POST.get("pricing_unit")
        if weight_based == "kg":
            unit = True
        else:
            unit = False
        product = Product.objects.create(name=name, barcode=barcode, sales_price=sales_price, vendor_cost=vendor_cost, qty=qty, weight_based=unit)
        return redirect("/products/")
    return render(request, "product-add.html")