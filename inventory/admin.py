# inventory/admin.py
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect, render
import csv, io

from .models import Hub, User, SKU, Inventory, InventoryLog, Shipment, ShipmentLine, HubSKU


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    search_fields = ("name", "city")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "hub", "is_superuser", "is_staff", "is_active")
    list_filter = ("role", "is_superuser", "is_staff", "is_active", "hub")
    search_fields = ("username", "email")


class HubSKUInline(admin.TabularInline):
    model = HubSKU
    extra = 0
    autocomplete_fields = ("hub",)


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "barcode", "low_stock_threshold")
    search_fields = ("sku", "name", "barcode")
    inlines = [HubSKUInline]
    change_list_template = "admin/inventory/sku/change_list.html"  # <-- adds our upload button

    def get_urls(self):
        """Add a custom URL under the SKU admin for CSV uploads."""
        urls = super().get_urls()
        my_urls = [
            path("upload-csv/", self.admin_site.admin_view(self.upload_csv), name="inventory_sku_upload_csv"),
        ]
        return my_urls + urls

    def upload_csv(self, request):
        """
        Admin view to upload SKUs via CSV.
        Expected columns (header row optional but recommended):
            sku, name, barcode, low_stock_threshold
        """
        if request.method == "POST":
            f = request.FILES.get("file")
            if not f:
                messages.error(request, "Please choose a CSV file to upload.")
                return redirect("admin:inventory_sku_changelist")

            # Read CSV
            try:
                txt = io.TextIOWrapper(f.file, encoding="utf-8")
                reader = csv.DictReader(txt)
            except Exception as e:
                messages.error(request, f"Could not read CSV: {e}")
                return redirect("admin:inventory_sku_changelist")

            created = 0
            updated = 0
            errors = 0

            for idx, row in enumerate(reader, start=2):  # start=2 to account for header as row 1
                try:
                    sku_code = (row.get("sku") or "").strip()
                    name = (row.get("name") or "").strip()
                    barcode = (row.get("barcode") or "").strip()
                    low_raw = (row.get("low_stock_threshold") or "").strip()
                    low = int(low_raw) if low_raw else 5

                    if not sku_code or not name:
                        errors += 1
                        continue

                    obj, is_created = SKU.objects.update_or_create(
                        sku=sku_code,
                        defaults={
                            "name": name,
                            "barcode": barcode,
                            "low_stock_threshold": low,
                        },
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1
                except Exception:
                    errors += 1

            if created or updated:
                messages.success(
                    request,
                    f"CSV processed. Created: {created}, Updated: {updated}. "
                    + (f"Errors: {errors}." if errors else "")
                )
            else:
                messages.warning(
                    request,
                    "No SKUs were created or updated. Check your CSV headers/rows."
                )
            return redirect("admin:inventory_sku_changelist")

        # GET – render a tiny upload form within admin chrome
        return render(request, "admin/inventory/sku/upload_csv.html", {})


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("hub", "sku", "qty")
    list_filter = ("hub",)
    search_fields = ("sku__sku", "sku__name", "hub__name")


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "hub", "sku", "change", "note")
    list_filter = ("hub", "user")
    search_fields = ("sku__sku", "sku__name", "hub__name", "user__username")


class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    extra = 0
    autocomplete_fields = ("sku",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "dest_hub", "status", "created_at")
    list_filter = ("status", "dest_hub")
    inlines = [ShipmentLineInline]
