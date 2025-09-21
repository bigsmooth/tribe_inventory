from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from .models import Inventory

def healthcheck(request): return HttpResponse("ok")

@login_required
def home(request):
    recent = Inventory.objects.select_related('hub','sku').all()[:10]
    return render(request, 'home.html', {'recent': recent})
