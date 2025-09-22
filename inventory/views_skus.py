# inventory/views_skus.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
import csv

from .forms import SKUCSVUploadForm, SKUAssignForm, HubFilterForm
from .models import SKU, Hub, HubSKU

def admin_required(view):
    return login_required(user_passes_test(lambda u: u.is_superuser)(view))

@admin_required
def skus_upload(request):
    """
    Admin-only: Upload a CSV to create/update SKUs and (optionally) assign hubs.
    Expected headers: sku,name,barcode,low_stock_threshold,hubs
    hubs = "Hub 1, Hub 2" (comma-separated names).
    """
    if request.method == "POST":
        form = SKUCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            clear_assignments = form.cleaned_data["clear_assignments"]
            default_threshold = form.cleaned_data["default_threshold"] or 5

            # Read CSV (support UTF-8 with BOM)
            text = f.read().decode("utf-8-sig", errors="ignore").splitlines()
            reader = csv.DictReader(text)
            reader.fieldnames = [h.lower().strip() for h in (reader.fieldnames or [])]

            required = {"sku", "name"}
            missing = required - set(reader.fieldnames)
            if missing:
                messages.error(request, f"CSV missing required column(s): {', '.join(sorted(missing))}")
                return redirect("skus_upload")

            created, updated, linked = 0, 0, 0
            with transaction.atomic():
                for row in reader:
                    sku_code = (row.get("sku") or "").strip()
                    name = (row.get("name") or "").strip()
                    barcode = (row.get("barcode") or "").strip()
                    th_raw = (row.get("low_stock_threshold") or "").strip()
                    hubs_raw = (row.get("hubs") or "").strip()

                    if not sku_code or not name:
                        continue

                    try:
                        threshold = int(th_raw) if th_raw != "" else default_threshold
                    except ValueError:
                        threshold = default_threshold

                    obj, was_created = SKU.objects.update_or_create(
                        sku=sku_code,
                        defaults={
                            "name": name,
                            "barcode": barcode,
                            "low_stock_threshold": threshold,
                        },
                    )
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1

                    if clear_assignments:
                        HubSKU.objects.filter(sku=obj).delete()

                    if hubs_raw:
                        hub_names = [h.strip() for h in hubs_raw.split(",") if h.strip()]
                        for hub_name in hub_names:
                            hub, _ = Hub.objects.get_or_create(name=hub_name)
                            link, link_created = HubSKU.objects.get_or_create(
                                hub=hub, sku=obj, defaults={"active": True}
                            )
                            if not link.active:
                                link.active = True
                                link.save(update_fields=["active"])
                            if link_created:
                                linked += 1

            messages.success(
                request,
                f"Import complete — created: {created}, updated: {updated}, links created: {linked}"
            )
            return redirect("skus_by_hub")
    else:
        form = SKUCSVUploadForm()

    return render(request, "skus_upload.html", {"form": form})

@admin_required
def skus_by_hub(request, hub_id=None):
    """
    Admin-only: Browse SKUs by hub. If no hub chosen, show a hub picker + high-level counts.
    """
    hubs = Hub.objects.order_by("name")
    hub = None
    rows = []
    totals = {"sku_count": 0}

    if hub_id:
        hub = get_object_or_404(Hub, id=hub_id)
        # SKUs assigned to this hub via HubSKU (active links)
        rows = (
            SKU.objects.filter(hubsku__hub=hub, hubsku__active=True)
            .distinct()
            .order_by("sku")
        )
        totals["sku_count"] = rows.count()

    # small hub filter form (for top bar)
    filter_form = HubFilterForm(initial={"hub": hub.id if hub else None})
    return render(
        request,
        "skus_by_hub.html",
        {"hubs": hubs, "hub": hub, "rows": rows, "totals": totals, "filter_form": filter_form},
    )

@admin_required
def sku_assign(request, sku_id):
    """
    Admin-only: Checkbox assignment of hubs for a single SKU.
    """
    sku = get_object_or_404(SKU, id=sku_id)

    if request.method == "POST":
        form = SKUAssignForm(request.POST, instance=sku)
        if form.is_valid():
            # Save direct M2M for convenience
            hubs = form.cleaned_data["hubs"]
            # Keep HubSKU as source of truth for per-hub flags (active, reorder_point)
            # First, deactivate existing links not in selection; then ensure links exist for selected.
            existing_links = HubSKU.objects.filter(sku=sku)
            keep_ids = set(h.id for h in hubs)
            for link in existing_links:
                if link.hub_id in keep_ids:
                    if not link.active:
                        link.active = True
                        link.save(update_fields=["active"])
                else:
                    if link.active:
                        link.active = False
                        link.save(update_fields=["active"])
            # Create missing links
            for hub in hubs:
                HubSKU.objects.get_or_create(hub=hub, sku=sku, defaults={"active": True})

            # Also sync SKU.hubs (M2M) so admin filters & forms stay intuitive
            sku.hubs.set(hubs)

            messages.success(request, f"Updated hub assignments for {sku.sku} — {sku.name}")
            return redirect("skus_by_hub")
    else:
        form = SKUAssignForm(instance=sku)

    return render(request, "sku_assign.html", {"form": form, "sku": sku})
