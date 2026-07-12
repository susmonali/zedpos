from django.db import models
from django.utils import timezone

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=100)
    vendor_cost = models.IntegerField()
    sales_price = models.IntegerField()
    barcode = models.CharField(max_length=100)
    qty = models.FloatField()
    weight_based = models.BooleanField(default=False, null=True, blank=True)
    active = models.BooleanField(null=True, blank=True, default=True)

    def __str__(self):
        return self.name

class Sale(models.Model):
    created_at = models.DateTimeField()
    total = models.IntegerField()

    def __str__(self):
        return f"{self.id} - {timezone.localtime(self.created_at)}"


class SaleItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    price = models.IntegerField()
    qty = models.FloatField()
    profit = models.FloatField()

    def __str__(self):
        return self.product.name
    
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Expense Categories"
        verbose_name = "Expense Category"
    
class Expense(models.Model):
    expense = models.IntegerField()
    reason = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.expense}"
    
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.FloatField()
    created_at = models.DateTimeField()
    paid = models.IntegerField()
    reference = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.product.name