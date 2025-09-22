# inventory/urls.py
from django.urls import path
from .views import (
    healthcheck, home, inventory_list, inventory_adjust,
    logs_list, logs_export_csv, shipments_list, shipment_new, shipment_receive,
    logout_get,
)
from . import views_skus  # NEW

urlpatterns = [
    # Health & auth
    path("health/", healthcheck, name="healthcheck"),
    path("logout/", logout_get, name="logout_get"),

    # Home / dashboard
    path("", home, name="home"),

    # Inventory
    path("inventory/", inventory_list, name="inventory_list"),
    path("inventory/<int:hub_id>/<int:sku_id>/adjust/", inventory_adjust, name="inventory_adjust"),

    # Logs
    path("logs/", logs_list, name="logs_list"),
    path("logs/export.csv", logs_export_csv, name="logs_export_csv"),

    # Shipments
    path("shipments/", shipments_list, name="shipments_list"),
    path("shipments/new/", shipment_new, name="shipment_new"),
    path("shipments/<int:shipment_id>/receive/", shipment_receive, name="shipment_receive"),

    # ---- NEW: SKU admin UI ----
    path("skus/upload/", views_skus.skus_upload, name="skus_upload"),
    path("skus/by-hub/", views_skus.skus_by_hub, name="skus_by_hub"),
    path("skus/by-hub/<int:hub_id>/", views_skus.skus_by_hub, name="skus_by_hub_detail"),
    path("skus/<int:sku_id>/assign/", views_skus.sku_assign, name="sku_assign"),
]
