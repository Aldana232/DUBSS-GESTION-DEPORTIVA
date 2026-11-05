"""
config/celery.py
Aplicación Celery del proyecto. Worker y beat se ejecutan como servicios aparte (docker-compose).
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("dubss")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
