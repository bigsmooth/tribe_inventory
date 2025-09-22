import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from inventory.models import SKU, Hub, HubSKU

class Command(BaseCommand):
    help = (
        "Import or update SKUs from a CSV.\n"
        "Expected headers (case-insensitive): sku,name,barcode,low_stock_threshold,hubs\n"
        "- hubs = optional comma-separated list of hub names to assign (e.g. \"Hub 1, Hub 2\").\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument(
            "--clear-hub-assignments",
            action="store_true",
            help="If set, will clear existing Hub assignments for each SKU before applying CSV hubs."
        )
        parser.add_argument(
            "--default-threshold",
            type=int,
            default=5,
            help="Default low_stock_threshold if missing/blank (default: 5)."
        )

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        default_threshold = int(opts["default_threshold"])
        clear_assignments = bool(opts["clear_hub_assignments"])

        created_count = 0
        updated_count = 0
        assigned_links = 0

        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # normalize headers → lowercase
            reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

            required = {"sku", "name"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

            for row in reader:
                sku_code = (row.get("sku") or "").strip()
                name = (row.get("name") or "").strip()
                barcode = (row.get("barcode") or "").strip()
                th_raw = (row.get("low_stock_threshold") or "").strip()
                hubs_raw = (row.get("hubs") or "").strip()  # e.g. "Hub 1, Hub 3"

                if not sku_code or not name:
                    self.stdout.write(self.style.WARNING(f"Skipping row missing sku/name: {row}"))
                    continue

                # threshold
                try:
                    threshold = int(th_raw) if th_raw != "" else default_threshold
                except ValueError:
                    threshold = default_threshold

                sku_obj, created = SKU.objects.update_or_create(
                    sku=sku_code,
                    defaults={
                        "name": name,
                        "barcode": barcode,
                        "low_stock_threshold": threshold,
                    },
                )
                if created:
                    created_count += 1
                    action = "created"
                else:
                    updated_count += 1
                    action = "updated"

                # hub assignments
                if clear_assignments:
                    HubSKU.objects.filter(sku=sku_obj).delete()

                if hubs_raw:
                    hub_names = [h.strip() for h in hubs_raw.split(",") if h.strip()]
                    for hub_name in hub_names:
                        hub, _ = Hub.objects.get_or_create(name=hub_name)
                        link, link_created = HubSKU.objects.get_or_create(hub=hub, sku=sku_obj, defaults={"active": True})
                        if not link.active:
                            link.active = True
                            link.save(update_fields=["active"])
                        if link_created:
                            assigned_links += 1

                self.stdout.write(self.style.SUCCESS(f"{action}: {sku_obj.sku} ({sku_obj.name})"))

        self.stdout.write(self.style.NOTICE(f"\nSummary:"))
        self.stdout.write(self.style.NOTICE(f"  SKUs created: {created_count}"))
        self.stdout.write(self.style.NOTICE(f"  SKUs updated: {updated_count}"))
        self.stdout.write(self.style.NOTICE(f"  Hub↔SKU links created: {assigned_links}"))
