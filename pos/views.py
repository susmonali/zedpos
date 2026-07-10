from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Avg
from django.utils.timezone import localdate, localtime
from .models import *

from datetime import datetime, timedelta, time

import json

def dashboard(request):
    now = localtime().now()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = now.date() - timedelta(days=1)
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
            sale_item = SaleItem.objects.create(product=product, sale=sale, price=qty*price, qty=qty)
            sale.total+=(qty*price)
        sale.save()
        return JsonResponse({"status": "ok", "sale_id":last_sale.id, "next_sale_id": last_sale.id+1, "sale_total":sale.total})


        
    return render(request, "pos.html", context)