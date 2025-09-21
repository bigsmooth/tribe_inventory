from django.db import models
from django.contrib.auth.models import AbstractUser

class Hub(models.Model):
    name = models.CharField(max_length=64)
    city = models.CharField(max_length=64, blank=True)
    def __str__(self): return self.name

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=[
        ('ADMIN','ADMIN'),('HUB','HUB'),('RETAIL','RETAIL'),('SUPPLIER','SUPPLIER')
    ], default='HUB')
    hub = models.ForeignKey(Hub, null=True, blank=True, on_delete=models.SET_NULL)
    def __str__(self): return f"{self.username} ({self.role})"

class SKU(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    barcode = models.CharField(max_length=64, blank=True)
    low_stock_threshold = models.IntegerField(default=5)
    def __str__(self): return f"{self.sku} - {self.name}"

class Inventory(models.Model):
    hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    qty = models.IntegerField(default=0)
    class Meta: unique_together = ('hub','sku')
    def __str__(self): return f"{self.hub} | {self.sku} = {self.qty}"

class InventoryLog(models.Model):
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    change = models.IntegerField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Shipment(models.Model):
    supplier = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='supplier_user')
    dest_hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=[('PENDING','PENDING'),('RECEIVED','RECEIVED')], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

class ShipmentLine(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='lines')
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    qty = models.IntegerField()
