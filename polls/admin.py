from django.contrib import admin

from .models import Choice, Question

# 관리자 페이지(/admin/)에 모델을 등록 → "+ 추가" 로 데이터를 넣을 수 있다
admin.site.register(Question)
admin.site.register(Choice)
