# inventory/views.py

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from django.utils.timezone import now
from django.db.models import Sum, Count

import csv
import math

from .models import (
    Inventory, InventoryLog, Hub, SKU,
    Shipment, ShipmentLine,
)
from .services import adjust_stock
from .utils import get_visible_hubs          # make sure inventory/utils.py exists
from .receiving import receive_shipment      # make sure inventory/receiving.py exists
from .forms import AdjustStockForm           # make sure inventory/forms.py exists


# ------------------------
# Helpers / Permissions
# ------------------------

def require_role(*roles):
    """
    Allow only certain roles. Superusers (Kevin) bypass checks.
    Usage:
      @require_role("HUB")
      def some_view(...):
          ...
    """
    def deco(view):
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view(request, *args, **kwargs)
            if request.user.is_authenticated and getattr(request.user, "role", None) in roles:
                return view(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return deco


# ------------------------
# Health & Auth
# ------------------------

def healthcheck(request):
    return HttpResponse("ok")


def logout_get(request):
    """Allow logging out via GET, then redirect to login."""
    logout(request)
    return redirect("login")


# ------------------------
# Home / Dashboard (KISS)
# ------------------------

@login_required
def home(request):
    """
    Friendly, simple dashboard:
      ✅ User Greeting Block (name, role, hub name, emoji)
      ✅ Quick Stats (SKUs, total qty, low-stock alerts)
      ✅ Encouragement / Context (today, friendly message, rotating quote)
      ✅ Recent Actions (last 3 inventory changes in user-visible hubs)
    """
    user = request.user
    visible_hubs = get_visible_hubs(user)  # queryset (may be empty)

    # --- Role label ---
    role_label = "Admin" if user.is_superuser else (
        getattr(user, "role", None) or "Hub Manager"
    )

    # --- Hub display (single hub gets nice label, multi -> list) ---
    hub_names = list(visible_hubs.values_list("name", flat=True))
    if len(hub_names) == 1:
        hub_display = hub_names[0]  # e.g., "Hub 3 – California"
    elif len(hub_names) > 1:
        hub_display = ", ".join(hub_names)
    else:
        hub_display = "No hub assigned"

    # --- Emojis (fun) ---
    emojis = {"box": "📦", "truck": "🚚", "socks": "🧦", "rocket": "🚀", "strong": "💪"}

    # --- Date / friendly message / rotating quote ---
    today = now()  # timezone-aware
    friendly_msg = f"Keep the socks moving, {emojis['rocket']} {user.username.capitalize()}! Your hub is the heartbeat of TTT."
    quotes = [
        f"Thick Thigh Tribe Strong {emojis['strong']}",
        f"Small steps, big stacks {emojis['box']}",
        f"Move smart, move steady {emojis['truck']}",
        f"Inventory zen: fewer surprises, more {emojis['socks']}",
    ]
    # rotate quote by day of year
    day_index = int(today.strftime("%j"))
    rotating_quote = quotes[day_index % len(quotes)]

    # --- Scoped inventory queryset (only hubs the user can see; admin sees all) ---
    inv_qs = Inventory.objects.select_related("hub", "sku")
    if not user.is_superuser:
        if visible_hubs.exists():
            inv_qs = inv_qs.filter(hub__in=visible_hubs)
        else:
            inv_qs = inv_qs.none()

    # --- Quick stats ---
    # SKUs assigned (distinct by SKU across scope)
    total_skus = inv_qs.values("sku").distinct().count()

    # Total stock on hand (sum of qty across scope)
    total_qty = inv_qs.aggregate(total=Sum("qty"))["total"] or 0

    # Low stock alerts (aggregate by SKU across scope)
    LOW_STOCK_THRESHOLD = 10
    low_stock_rows = (
        inv_qs.values("sku__sku")
             .annotate(total=Sum("qty"))
             .filter(total__lt=LOW_STOCK_THRESHOLD)
             .order_by("total")[:10]
    )
    low_stock = [{"sku": r["sku__sku"], "qty": r["total"] or 0} for r in low_stock_rows]

    # --- Recent actions (always show last 3 in scope) ---
    logs_qs = InventoryLog.objects.select_related("user", "hub", "sku").order_by("-created_at")
    if not user.is_superuser:
        if visible_hubs.exists():
            logs_qs = logs_qs.filter(hub__in=visible_hubs)
        else:
            logs_qs = logs_qs.none()
    recent_logs = list(logs_qs[:3])

    # --- Friendly welcome line ---
    welcome = f"Welcome {user.username.capitalize()}! {emojis['socks']}  "
    if visible_hubs.exists():
        welcome += f"You’re managing: {hub_display}."
    else:
        welcome += "You don’t have a hub assigned yet."

    # --- A short recent inventory peek (global scope teaser – keep for consistency) ---
    recent_inventory = inv_qs.order_by("-id")[:10]

    ctx = {
        # greeting block
        "welcome": welcome,
        "role_label": role_label,
        "hub_display": hub_display,
        "emojis": emojis,

        # stats
        "total_skus": total_skus,
        "total_qty": total_qty,
        "low_stock": low_stock,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,

        # encouragement / context
        "today": today,
        "friendly_msg": friendly_msg,
        "rotating_quote": rotating_quote,

        # recent activity
        "recent_logs": recent_logs,

        # existing fields for the rest of the page
        "user": user,
        "hubs": visible_hubs,
        "recent": recent_inventory,
    }
    return render(request, "home.html", ctx)


# ------------------------
# Inventory: list & adjust
# ------------------------

@login_required
def inventory_list(request):
    """
    Show inventory for the hubs the user can see.
    Superusers see all; hub managers see only their hub.
    """
    visible_hubs = get_visible_hubs(request.user)
    rows = (
        Inventory.objects
        .select_related("hub", "sku")
        .filter(hub__in=visible_hubs)
        .order_by("hub__name", "sku__sku")
    )
    scope = "All hubs (admin)" if request.user.is_superuser else (
        ", ".join(visible_hubs.values_list("name", flat=True)) or "No hub assigned"
    )
    return render(request, "inventory_list.html", {"rows": rows, "scope": scope})


@login_required
def inventory_adjust(request, hub_id, sku_id):
    """
    Adjust stock for a given hub + SKU.
    Only allowed if the hub is within the user's visible hubs (or superuser).
    """
    visible_hubs = get_visible_hubs(request.user)
    hub = get_object_or_404(Hub, id=hub_id)
    if hub not in list(visible_hubs):
        raise PermissionDenied("You do not have access to this hub.")

    sku = get_object_or_404(SKU, id=sku_id)

    if request.method == "POST":
        form = AdjustStockForm(request.POST)
        if form.is_valid():
            delta = form.cleaned_data["delta"]
            note = form.cleaned_data.get("note") or ""
            try:
                adjust_stock(request.user, hub, sku, delta, note=note)
                messages.success(request, f"Adjusted {sku.sku} at {hub.name} by {delta}.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("inventory_list")
    else:
        form = AdjustStockForm(initial={"hub_id": hub.id, "sku_id": sku.id})

    return render(request, "inventory_adjust.html", {"form": form, "hub": hub, "sku": sku})


# ------------------------
# Logs: list & CSV export
# ------------------------

@login_required
def logs_list(request):
    logs = (
        InventoryLog.objects
        .select_related("user", "hub", "sku")
        .order_by("-created_at")
    )[:200]
    return render(request, "logs_list.html", {"logs": logs})


@login_required
def logs_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    filename = f"inventory_logs_{now().date()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    w = csv.writer(response)
    w.writerow(["created_at", "user", "hub", "sku", "change", "note"])
    for log in InventoryLog.objects.select_related("user", "hub", "sku").order_by("-created_at"):
        w.writerow([
            log.created_at,
            getattr(log.user, "username", ""),
            log.hub.name,
            log.sku.sku,
            log.change,
            log.note
        ])
    return response


# ------------------------
# Shipments: list / new / receive
# ------------------------

@login_required
def shipments_list(request):
    """
    Superusers: see all shipments.
    Hub managers: see shipments for their hub only.
    """
    visible_hubs = get_visible_hubs(request.user)
    qs = Shipment.objects.select_related("dest_hub", "supplier").order_by("-created_at")
    if not request.user.is_superuser:
        qs = qs.filter(dest_hub__in=visible_hubs)
    ships = qs[:100]
    return render(request, "shipments_list.html", {"ships": ships})


@require_role("SUPPLIER")  # change/remove as you prefer
@login_required
def shipment_new(request):
    """
    Minimal shipment creator:
    - Choose destination hub
    - Lines can be added in admin for now
    """
    if request.method == "POST":
        hub_id = int(request.POST["hub_id"])
        hub = get_object_or_404(Hub, id=hub_id)
        s = Shipment.objects.create(supplier=request.user, dest_hub=hub, status="PENDING")
        messages.success(request, f"Created shipment #{s.id} to {hub.name}. Add lines in admin, then Receive.")
        return redirect("shipments_list")

    # Suppliers may ship to any hub; hub managers would only see their own hub if you prefer
    hubs = Hub.objects.all().order_by("name")
    return render(request, "shipment_new.html", {"hubs": hubs})


@login_required
def shipment_receive(request, shipment_id):
    """
    Mark a shipment as received and apply inventory deltas.
    Hub managers can only receive for their own hub.
    """
    s = get_object_or_404(Shipment.objects.select_related("dest_hub"), id=shipment_id)

    # Gate: only superuser or the manager of the destination hub
    visible_hubs = get_visible_hubs(request.user)
    if s.dest_hub not in list(visible_hubs):
        raise PermissionDenied("You do not have access to receive this shipment.")

    if request.method == "POST":
        receive_shipment(request.user, s)
        messages.success(request, f"Shipment {s.id} received.")
        return redirect("shipments_list")

    return render(request, "shipment_receive.html", {"s": s})
