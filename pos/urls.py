from django.urls import path, include
from .views import *

urlpatterns = [
    path('', dashboard, name="dashboard"),
    path('pos/', point_of_sale, name="pos"),
    path('products/', products_list, name="products"),
    path('products/add/', product_add, name="product_add"),
]
