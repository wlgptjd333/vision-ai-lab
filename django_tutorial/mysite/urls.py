from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("polls/", include("polls.urls")),  # polls 앱의 URL 연결
    path("movies/", include("movies.urls")),  # 실습해보기_Part1 영화 추천
    path("admin/", admin.site.urls),
]
