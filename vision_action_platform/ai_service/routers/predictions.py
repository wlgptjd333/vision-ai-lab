"""POST /predict/video — Celery Worker 가 보낸 영상 한 건을 사람별로 예측해 JSON 으로 돌려준다.

응답 규칙 (Worker 가 구분하는 방법)
  200 + predictions 1개 이상   정상
  200 + predictions 빈 목록    영상은 정상, 사람을 못 찾았거나 판단할 만큼 보이지 않음 → message 에 이유
  400                         영상을 읽을 수 없음·확장자 오류 → detail 에 이유
  413                         파일이 너무 큼
  503                         모델이 준비되지 않음
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from services.action_inference import predict_tracks
from services.pose_pipeline import VideoReadError, extract_tracks

router = APIRouter(tags=["predictions"])
ALLOWED_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@router.post("/predict/video")
def predict_video(request: Request, file: UploadFile = File(...)):
    bundle = request.app.state.bundle
    if not bundle.ready:
        raise HTTPException(503, f"모델이 준비되지 않았습니다: {bundle.error}")
    cfg = bundle.config
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다 ({ext or '확장자 없음'}). MP4 영상을 보내 주세요.")

    started = time.perf_counter()
    fd, tmp = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as out:
            shutil.copyfileobj(file.file, out, length=1024 * 1024)
        size_mb = os.path.getsize(tmp) / 1e6
        if size_mb > cfg["max_upload_mb"]:
            raise HTTPException(413, f"파일이 너무 큽니다 ({size_mb:.0f} MB > {cfg['max_upload_mb']} MB).")
        try:
            video = extract_tracks(tmp, bundle.pose_model, cfg, request.app.state.device)
        except VideoReadError as exc:
            raise HTTPException(400, str(exc)) from exc
        predictions, skipped = predict_tracks(video, bundle)
    finally:
        os.remove(tmp)

    if not video.tracks:
        message = "영상에서 사람을 찾지 못했습니다."
    elif not predictions:
        message = "사람은 보였지만 관절이 충분히 보이지 않아 동작을 판단하지 못했습니다."
    else:
        message = ""
    return {
        "ok": True,
        "message": message,
        "video": {"frames": video.frames, "fps": video.fps, "seconds": video.seconds,
                  "width": video.width, "height": video.height},
        "processing_seconds": round(time.perf_counter() - started, 2),
        "pose_seconds": video.pose_seconds,
        "uncertain_below": cfg["uncertain_below"],
        "predictions": predictions,
        "skipped_tracks": skipped,
    }
