"""Django 설정. 비밀값·주소는 모두 환경변수(.env)에서 읽는다 — 코드와 GitHub 에는 넣지 않는다."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-secret")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8100,http://127.0.0.1:8100")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "analyses",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL (Docker Compose). POSTGRES_HOST 가 없으면 로컬 테스트용 SQLite
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "vision_action"),
            "USER": os.environ.get("POSTGRES_USER", "vision_action"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Docker 이미지(collectstatic 을 한 곳)에서만 압축·해시 파일명을 쓰고, 로컬 테스트에서는 원래 파일 그대로
_COLLECTED = env_bool("STATIC_MANIFEST", False)          # Dockerfile 에서 1
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if _COLLECTED and not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# 업로드 영상·IP Webcam 수집 영상: Django 와 Celery 가 같은 볼륨(/app/media)을 공유
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "analyses:index"
LOGOUT_REDIRECT_URL = "login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Celery — Redis 는 작업 대기열·상태만, 오래 남길 결과는 PostgreSQL
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_TIME_LIMIT = 15 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1          # 영상 분석은 오래 걸리므로 하나씩 가져간다
CELERY_TIMEZONE = TIME_ZONE

# FastAPI 추론 서버 — 컨테이너 사이에서는 localhost 가 아니라 Compose 서비스 이름으로 부른다
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8001")
FASTAPI_TIMEOUT_SECONDS = int(os.environ.get("FASTAPI_TIMEOUT_SECONDS", "600"))

# 업로드 제한
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "100"))
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

# IP Webcam: 허용한 카메라만 이름으로 고른다. 사용자가 임의 URL 을 입력하지 못한다.
#   IPWEBCAM_CAMERAS="phone=http://192.168.0.10:8080/video,phone2=http://..."
IPWEBCAM_CAMERAS = dict(item.split("=", 1) for item in env_list("IPWEBCAM_CAMERAS") if "=" in item)
CAPTURE_SECONDS = float(os.environ.get("CAPTURE_SECONDS", "8"))
CAPTURE_CONNECT_TIMEOUT_SECONDS = float(os.environ.get("CAPTURE_CONNECT_TIMEOUT_SECONDS", "10"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# 이 값보다 Confidence 가 낮으면 화면에 '판단 불확실'로 표시 (FastAPI 응답에도 같은 값이 온다)
UNCERTAIN_BELOW = float(os.environ.get("UNCERTAIN_BELOW", "0.25"))
