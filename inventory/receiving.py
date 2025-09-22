# inventory/receiving.py
from .models import Shipment
from .services import adjust_stock

def receive_shipment(user, shipment: Shipment):
    """
    Apply all shipment lines to inventory and mark as received.
    """
    if shipment.status == "RECEIVED":
        return
    for line in shipment.lines.select_related("sku"):
        adjust_stock(
            user=user,
            hub=shipment.dest_hub,
            sku=line.sku,
            delta=line.qty,
            note=f"Shipment {shipment.id}",
        )
    shipment.status = "RECEIVED"
    shipment.save()
