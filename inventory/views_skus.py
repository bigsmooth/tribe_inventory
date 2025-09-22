# inventory/views_skus.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
import csv, io

from .models import SKU, Hub, HubSKU
from .utils import get_visible_hubs

@login_required
def skus_upload(request):
    """Upload a CSV of SKUs with columns: sku,name,barcode,low_stock_threshold"""
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        data = f.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        created = 0
        updated = 0
        for row in reader:
            sku_code = (row.get("sku") or "").strip()
            if not sku_code:
                continue
            name = (row.get("name") or "").strip()
            barcode = (row.get("barcode") or "").strip()
            try:
                low = int(row.get("low_stock_threshold") or 5)
            except:
                low = 5
            obj, is_new = SKU.objects.update_or_create(
                sku=sku_code,
                defaults={"name": name or sku_code, "barcode": barcode, "low_stock_threshold": low},
            )
            created += 1 if is_new else 0
            updated += 0 if is_new else 1
        messages.success(request, f"Upload complete. Created {created}, Updated {updated}.")
        return redirect("skus_upload")

    return render(request, "skus_upload.html")

@login_required
def skus_by_hub(request, hub_id=None):
    """Show SKUs assigned to hubs (admin sees all; hub mgr sees own)."""
    hubs = get_visible_hubs(request.user)
    if request.user.is_superuser:
        hubs = Hub.objects.all()

    if hub_id:
        hub = get_object_or_404(hubs, id=hub_id)
        assignments = HubSKU.objects.select_related("hub", "sku").filter(hub=hub).order_by("sku__sku")
        return render(request, "skus_by_hub.html", {"hub": hub, "assignments": assignments, "hubs": hubs})

    # no hub selected — show first or list
    hub = hubs.first()
    assignments = HubSKU.objects.select_related("hub", "sku").filter(hub=hub).order_by("sku__sku") if hub else []
    return render(request, "skus_by_hub.html", {"hub": hub, "assignments": assignments, "hubs": hubs})

@login_required
def sku_assign(request, sku_id):
    """Assign/unassign an SKU to hubs (admin only)."""
    if not request.user.is_superuser:
        raise PermissionDenied
    sku = get_object_or_404(SKU, id=sku_id)

    if request.method == "POST":
        action = request.POST.get("action")
        hub_id = request.POST.get("hub_id")
        hub = get_object_or_404(Hub, id=hub_id)
        if action == "assign":
            HubSKU.objects.get_or_create(hub=hub, sku=sku)
            messages.success(request, f"Assigned {sku.sku} to {hub.name}.")
        elif action == "unassign":
            HubSKU.objects.filter(hub=hub, sku=sku).delete()
            messages.success(request, f"Removed {sku.sku} from {hub.name}.")
        return redirect("skus_by_hub_detail", hub_id=hub.id)

    hubs = Hub.objects.all().order_by("name")
    assigned_ids = set(HubSKU.objects.filter(sku=sku).values_list("hub_id", flat=True))
    return render(request, "sku_assign.html", {"sku": sku, "hubs": hubs, "assigned_ids": assigned_ids})
