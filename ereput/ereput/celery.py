from __future__ import absolute_import, unicode_literals
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ereput.settings')

app = Celery('ereput')
app.config_from_object('django.conf:settings')
 


# # Load task modules from all registered Django app configs.
#app.autodiscover_tasks()

