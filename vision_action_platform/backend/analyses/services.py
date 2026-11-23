"""FastAPI 추론 서버 호출. 영상 파일을 HTTP multipart 로 보낸다 (컨테이너끼리 파일 경로를 공유한다고 가정하지 않음)."""
from pathlib import Path

import requests
from django.conf import settings


class InferenceError(Exception):
    """사용자에게 그대로 보여 줄 수 있는 실패 사유"""


def predict_video(path: str) -> dict:
    url = settings.FASTAPI_URL.rstrip("/") + "/predict/video"
    try:
        with open(path, "rb") as f:
            resp = requests.post(url, files={"file": (Path(path).name, f, "video/mp4")},
                                 timeout=settings.FASTAPI_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        raise InferenceError("분석할 영상 파일을 찾지 못했습니다.") from exc
    except requests.Timeout as exc:
        raise InferenceError(f"AI 서버 응답 시간이 {settings.FASTAPI_TIMEOUT_SECONDS}초를 넘었습니다.") from exc
    except requests.ConnectionError as exc:
        raise InferenceError("AI 서버에 연결하지 못했습니다. 잠시 후 다시 시도하세요.") from exc
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text[:200]
        raise InferenceError(f"AI 서버 오류 ({resp.status_code}): {detail}")
    return resp.json()


def health() -> dict:
    try:
        return requests.get(settings.FASTAPI_URL.rstrip("/") + "/health", timeout=3).json()
    except (requests.RequestException, ValueError):
        return {"status": "unreachable"}
