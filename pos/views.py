from django.db.models.functions import ExtractHour
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, F, FloatField, ExpressionWrapper
from django.utils.timezone import localtime
from .models import *

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import calendar

import json

def percent_change(new_value, old_value):
    if old_value!=0:
        percent_change = ((new_value-old_value)/old_value)*100
    elif new_value>0:
        percent_change = 100
    else:
        percent_change = 0
    
    return percent_change


def aggregate_period(start, end):
    context = {
        "sales": Sale.objects.filter(created_at__date__range=(start, end)).aggregate(Sum("total"))["total__sum"] or 0,
        "profit": SaleItem.objects.filter(sale__created_at__date__range=(start, end)).aggregate(Sum("profit"))["profit__sum"] or 0,
        "expenses": Expense.objects.filter(created_at__date__range=(start, end)).aggregate(Sum("expense"))["expense__sum"] or 0,
        "start_date": start,
        "end_date": end,
    }
    return context

def dashboard(request):
    #custom_range
    custom_range_sales = {
        "sales": 0,
        "profit": 0,
        "expenses": 0,
    }

    start = request.GET.get("start_date")
    end = request.GET.get("end_date")
    custom_range_active = False
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            custom_range_sales = aggregate_period(start_date, end_date)
            custom_range_active = True
        except ValueError:
            pass


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

    percentage_change = percent_change(new_value=today_sales_total, old_value=yesterday_sales_total)

    difference = today_sales.count()-yesterday_sales.count()

    average_basket = today_sales.aggregate(Avg("total"))["total__avg"] or 0
    average_basket_yesterday = yesterday_sales.aggregate(Avg("total"))["total__avg"] or 0
    avg_percent_change = percent_change(new_value=average_basket, old_value=average_basket_yesterday)


    items_sold = SaleItem.objects.filter(sale__created_at__range=(today_midnight, now)
                                         ).aggregate(Sum("qty"))["qty__sum"] or 0
    items_sold_yesterday = SaleItem.objects.filter(sale__created_at__range=(yesterday_midnight, yesterday_current_time)
                                                   ).aggregate(Sum("qty"))["qty__sum"] or 0
    
    items_sold_change = percent_change(new_value=items_sold, old_value=items_sold_yesterday)


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
    yesterday_period = aggregate_period(yesterday, yesterday)
    week_period = aggregate_period(today - timedelta(days=7), today)
    month_param = request.GET.get("month")
    try:
        selected_month = datetime.strptime(month_param, "%Y-%m").date()
    except:
        selected_month = now.date().replace(day=1)
    month_name = selected_month.strftime("%B")
    prev_month_param = (selected_month - relativedelta(months=1)).strftime("%Y-%m")
    next_month_param = (selected_month + relativedelta(months=1)).strftime("%Y-%m")if selected_month < today.replace(day=1) else None
    last_day_num = calendar.monthrange(selected_month.year, selected_month.month)
    month_period = aggregate_period(selected_month, selected_month+timedelta(days=last_day_num[1]))

    context = {
        "prev_month_param": prev_month_param,
        "next_month_param": next_month_param, 
        "today_sales": today_sales,
        "custom_range_active": custom_range_active,
        "custom_sales": custom_range_sales["sales"],
        "custom_profit": custom_range_sales["profit"],
        "custom_expenses": custom_range_sales["expenses"],
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
        "top_sellers": top_sellers[:6],
        "yesterday_all_sales": yesterday_period["sales"],
        "yesterday_profit": yesterday_period["profit"],
        "yesterday_expenses": yesterday_period["expenses"],
        "days_7_all_sales": week_period["sales"],
        "days_7_profit": week_period["profit"],
        "days_7_expenses": week_period["expenses"],
        "month_all_sales": month_period["sales"],
        "month_profit": month_period["profit"],
        "month_expenses": month_period["expenses"],
        "month_name": month_name,
        "custom_range_sales": custom_range_sales,
    }
    return render(request, "dashboard.html", context)

def point_of_sale(request):
    last_sale = Sale.objects.last()
    context = {
        "products": Product.objects.filter(active=True),
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
            if qty>product.qty:
                return JsonResponse({"message": f"Not enough products! - { product.name }"})
            price = item.get('price')
            sale_item = SaleItem.objects.create(product=product, sale=sale, price=qty*price, qty=float(qty), profit=float((product.sales_price-product.vendor_cost)*qty))
            product.qty-=qty
            product.save()
            sale.total+=(qty*price)
        sale.save()
        return JsonResponse({
            "status": "ok",
            "sale_id": last_sale.id,
            "next_sale_id": last_sale.id + 1,
            "sale_total": sale.total,
            "updated_stock": {
                str(item.product.id): item.product.qty
                for item in SaleItem.objects.filter(sale=sale)
            }
        })
        
    return render(request, "pos.html", context)


def products_list(request):
    context = {
        "products": Product.objects.all().order_by("-active")
    }
    return render(request, "products.html", context)

def product_add(request):
    if request.method == "POST":
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

def product_detail(request, i):
    today = localtime().now().date()
    product = Product.objects.get(id=i)
    week = today - timedelta(days=7)
    sold_this_week = SaleItem.objects.filter(sale__created_at__date__range=(week, today), product__id=i).aggregate(Sum("qty"))["qty__sum"] or 0
    
    sale_history = SaleItem.objects.filter(sale__created_at__date__range=(week, today), product__id=i).order_by("-sale__created_at")[:50]

    days_7_profit = SaleItem.objects.filter(sale__created_at__date__range=(week, today), product=product).aggregate(Sum("profit"))["profit__sum"] or 0
    restock_history = Stock.objects.filter(created_at__date__range=(week, today), product=product)[:30]
    context = {
        "product": product,
        "sold_this_week": sold_this_week,
        "sale_history": sale_history,
        "days_7_profit": days_7_profit,
        "restock_history": restock_history, 
    }
    return render(request, "product-detail.html", context)

def delete_product(request, i):
    Product.objects.get(id=i).delete
    return redirect("/products/")

def archive_product(request, i):
    product = Product.objects.get(id=i)
    product.active = False
    product.save()
    return redirect("/products/")

def unarchive_product(request, i):
    product = Product.objects.get(id=i)
    product.active = True
    product.save()
    return redirect(f"/products/{i}/detail/")

def restock(request, i):
    product = Product.objects.get(id=i)
    now = localtime().now()
    if request.method == "POST":
        qty = request.POST.get("qty")
        paid = request.POST.get("paid")
        reference = request.POST.get("reference")
        product.qty += float(qty)
        product.save()
        Stock.objects.create(product=product, qty=qty, created_at=now, paid=paid, reference=reference)
    return redirect(f"/products/{i}/detail/")


def expenses(request):
    now = localtime().now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    month_beginning = today.replace(day=1)

    expenses = Expense.objects.all()
    todays_expenses = expenses.filter(created_at__date=today).aggregate(Sum("expense"))["expense__sum"] or 0
    yesterdays_expenses = expenses.filter(created_at__date=yesterday).aggregate(Sum("expense"))["expense__sum"] or 0
    weekly_expenses = expenses.filter(created_at__date__range=(last_week, today)).aggregate(Sum("expense"))["expense__sum"] or 0
    month_expenses = expenses.filter(created_at__date__range=(month_beginning, today)).aggregate(Sum("expense"))["expense__sum"] or 0

    #expense by category
    expenses_by_category = {
        item['reason__name']: item['total'] or 0 for item in expenses.values("reason__name").annotate(total=Sum('expense'))
        }

    category_most_expenses = expenses.values("reason__name").annotate(total=Sum("expense")).order_by("-total").first()

    context = {
        "expenses": expenses,
        "todays_expenses": todays_expenses,
        "yesterdays_expenses": yesterdays_expenses,
        "weekly_expenses": weekly_expenses,
        "month_expenses": month_expenses,
        "products": Product.objects.all().order_by("-active"),
        "category_most_expenses": category_most_expenses,
        "today": today,
        "categories": ExpenseCategory.objects.all()
    }
    return render(request, 'expenses.html', context)

def add_expense(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        category = ExpenseCategory.objects.get(id=int(request.POST.get("category")))
        date = request.POST.get("date")
        Expense.objects.create(expense=amount, reason=category, created_at=date)
    return redirect("/expenses/")