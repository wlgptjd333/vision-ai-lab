import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# settings.py 의 CELERY_ 로 시작하는 값을 읽는다 (브로커 주소 등)
app.config_from_object("django.conf:settings", namespace="CELERY")
# 설치된 앱마다 tasks.py 를 찾아 등록
app.autodiscover_tasks()
