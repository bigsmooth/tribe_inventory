import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tribe_inventory.settings')
application = get_wsgi_application()
