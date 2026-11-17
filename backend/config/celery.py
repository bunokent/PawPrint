"""Celery application with centralized task routing."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("pawprint")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
