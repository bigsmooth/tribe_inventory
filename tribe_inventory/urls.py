from django.contrib import admin
from django.urls import path, include
from inventory.views import home, healthcheck
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('healthz/', healthcheck, name='healthcheck'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('inventory/', include('inventory.urls')),
]
