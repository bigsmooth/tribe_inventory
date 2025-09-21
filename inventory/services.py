from django.db import transaction
from .models import Inventory, InventoryLog
def adjust_stock(user, hub, sku, delta, note=""):
    with transaction.atomic():
        inv, _ = Inventory.objects.select_for_update().get_or_create(hub=hub, sku=sku)
        new_qty = inv.qty + delta
        if new_qty < 0: raise ValueError("Insufficient stock")
        inv.qty = new_qty; inv.save()
        InventoryLog.objects.create(user=user, hub=hub, sku=sku, change=delta, note=note)
