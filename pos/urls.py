from django.urls import path, include
from .views import point_of_sale

urlpatterns = [
    path('pos/', point_of_sale, name="pos"),
]
