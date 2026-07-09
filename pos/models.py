from django.db import models

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=100)
    vendor_cost = models.IntegerField()
    sales_price = models.IntegerField()
    barcode = models.CharField(max_length=100)
    qty = models.IntegerField()
    weight_based = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return self.name

class Sale(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, auto_created=True)
    total = models.IntegerField()

    def __str__(self):
        return f"{self.id} - {self.created_at}"


class SaleItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    price = models.IntegerField()

    def __str__(self):
        return self.product.name