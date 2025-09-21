from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# import our GET-safe logout and home/health
from inventory.views import home, healthcheck, logout_get

urlpatterns = [
    path('admin/', admin.site.urls),

    # app pages
    path('', home, name='home'),
    path('healthz/', healthcheck, name='healthcheck'),

    # auth
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('logout/', logout_get, name='logout'),      # <-- OUR view (GET OK)

    # keep app urls empty for now
    path('inventory/', include('inventory.urls')),
]
