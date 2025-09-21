from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from inventory.views import home, healthcheck, logout_get  # our GET logout

urlpatterns = [
    path('admin/', admin.site.urls),

    # main dashboard + healthcheck
    path('', home, name='home'),
    path('healthz/', healthcheck, name='healthcheck'),

    # login
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),

    # ✅ ONLY this logout route
    path('logout/', logout_get, name='logout'),

    # app urls (must NOT include auth.urls)
    path('inventory/', include('inventory.urls')),
]
