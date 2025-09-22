# inventory/management/commands/seed_org.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Hub

"""
Seeds hubs + hub managers + (optionally) Kevin as superuser.
Safe to run multiple times (idempotent).
"""

HUBS = [
    ("Hub 1 – Stafford, VA", {"city": "Stafford, VA"}),
    ("Hub 2 – CT", {"city": "Connecticut"}),
    ("Hub 3 – Cali", {"city": "California"}),
    ("Retail", {"city": "—"}),
]

MANAGERS = [
    # username, role, hub_name, password
    ("carmen", "HUB", "Hub 3 – Cali", "ChangeMe!123"),
    ("slo",    "HUB", "Hub 1 – Stafford, VA", "ChangeMe!123"),
    ("fox",    "HUB", "Hub 2 – CT", "ChangeMe!123"),
    # Kevin is superuser; retail hub does not need a separate manager login
]

class Command(BaseCommand):
    help = "Create hubs and assign hub managers; ensure Kevin superuser exists (optional)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ensure-kevin-superuser",
            action="store_true",
            help="Create/ensure a superuser named 'kevin' with password 'ChangeMe!123' if missing.",
        )

    def handle(self, *args, **opts):
        User = get_user_model()

        # 1) Create hubs
        name_to_hub = {}
        for name, extra in HUBS:
            hub, created = Hub.objects.get_or_create(name=name, defaults=extra)
            name_to_hub[name] = hub
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} hub: {name}"))

        # 2) Create or update hub managers
        for username, role, hub_name, pwd in MANAGERS:
            hub = name_to_hub[hub_name]
            user, created = User.objects.get_or_create(username=username, defaults={
                "role": role,
            })
            # Set/Reset password only on create to avoid clobbering later
            if created:
                user.set_password(pwd)
                self.stdout.write(self.style.SUCCESS(f"Created user: {username} ({role})"))
            else:
                # keep existing password; just ensure role set
                if getattr(user, "role", None) != role:
                    user.role = role
                    self.stdout.write(f"Updated role for {username} -> {role}")

            # Assign hub
            if getattr(user, "hub_id", None) != hub.id:
                user.hub = hub
                self.stdout.write(f"Assigned {username} -> {hub.name}")

            user.is_staff = True  # allow admin access if you want them to use /admin
            user.save()

        # 3) Optionally ensure Kevin as superuser
        if opts.get("ensure_kevin_superuser"):
            kevin, created = User.objects.get_or_create(username="kevin", defaults={
                "role": "ADMIN",
            })
            if created:
                kevin.set_password("ChangeMe!123")
                self.stdout.write(self.style.SUCCESS("Created kevin (initial password: ChangeMe!123)"))
            # make sure Kevin is superuser/staff
            changed = False
            if not kevin.is_superuser:
                kevin.is_superuser = True; changed = True
            if not kevin.is_staff:
                kevin.is_staff = True; changed = True
            if getattr(kevin, "role", "") != "ADMIN":
                kevin.role = "ADMIN"; changed = True
            if changed:
                kevin.save()
                self.stdout.write(self.style.SUCCESS("Ensured kevin is superuser (ADMIN)"))

        self.stdout.write(self.style.SUCCESS("Seeding finished."))
