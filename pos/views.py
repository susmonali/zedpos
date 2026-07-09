from django.shortcuts import render
from django.http import JsonResponse
from .models import *

from datetime import datetime

import json

def dashboard(request):
    context = {
        
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
        sale = Sale.objects.create(created_at=datetime.now(), total=0)
        for key, item in products.items():
            product = Product.objects.get(id=key)
            qty = item.get('qty')
            if not qty:
                qty = item.get('weight')
            price = item.get('price')
            sale_item = SaleItem.objects.create(product=product, sale=sale, price=qty*price)
            sale.total+=(qty*price)
        sale.save()
        return JsonResponse({"status": "ok", "sale_id":last_sale.id, "next_sale_id": last_sale.id+1, "sale_total":sale.total})


        
    return render(request, "pos.html", context)