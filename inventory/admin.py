from django.contrib import admin
from .models import User, Hub, SKU, Inventory, InventoryLog, Shipment, ShipmentLine
admin.site.register(User)
admin.site.register(Hub)
admin.site.register(SKU)
admin.site.register(Inventory)
admin.site.register(InventoryLog)
admin.site.register(Shipment)
admin.site.register(ShipmentLine)
