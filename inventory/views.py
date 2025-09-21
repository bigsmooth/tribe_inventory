from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect

from .models import Inventory


def healthcheck(request):
    return HttpResponse("ok")


@login_required
def home(request):
    # simple dashboard: show last 10 inventory rows
    recent = Inventory.objects.select_related("hub", "sku").all()[:10]
    return render(request, "home.html", {"recent": recent})


def logout_get(request):
    """Allow logging out via simple GET, then redirect to login."""
    logout(request)
    return redirect("login")
