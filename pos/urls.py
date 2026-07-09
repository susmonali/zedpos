from django.urls import path, include
from .views import *

urlpatterns = [
    path('', dashboard, name="dashboard"),
    path('pos/', point_of_sale, name="pos"),
]
