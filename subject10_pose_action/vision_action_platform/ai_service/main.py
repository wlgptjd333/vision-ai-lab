"""AI 추론 서버. DB 는 만지지 않고, 영상을 받아 사람별 예측 JSON 만 돌려준다 (저장은 Django·Celery 몫)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import predictions
from services.model_loader import load_bundle


def resolve_device(requested: str):
    if requested != "auto":
        return requested
    try:
        import torch
        return 0 if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.bundle = load_bundle()          # 서버 시작 때 한 번만 → 요청마다 재사용
    app.state.device = resolve_device(app.state.bundle.config["device"])
    yield


app = FastAPI(title="Vision Action API",
              description="교과10 기본 6개 Action — YOLO Pose + ByteTrack + Random Forest (6일차 모델)",
              version="1.0.0", lifespan=lifespan)
app.include_router(predictions.router)


@app.get("/health")
def health():
    b = app.state.bundle
    return {"status": "ok" if b.ready else "model_not_ready", "device": str(app.state.device), "model": b.summary()}
