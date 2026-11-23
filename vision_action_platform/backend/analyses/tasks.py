"""Celery 작업: 영상 확보(업로드 파일 또는 IP Webcam 수집) → FastAPI 추론 → Django ORM 으로 결과·상태 저장."""
import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .camera_capture import CaptureError, capture_clip
from .models import AnalysisJob, PersonPrediction
from .services import InferenceError, predict_video

log = logging.getLogger(__name__)


def _fail(job: AnalysisJob, message: str) -> None:
    job.status = AnalysisJob.Status.FAILURE
    job.error_message = message
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at"])


@shared_task(bind=True)
def run_analysis(self, job_id: int) -> str:
    try:
        job = AnalysisJob.objects.get(pk=job_id)
    except AnalysisJob.DoesNotExist:
        return "missing"                         # 그 사이 사용자가 삭제함
    job.status = AnalysisJob.Status.STARTED
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        if job.input_type == AnalysisJob.InputType.IPWEBCAM:
            rel = Path("videos") / "ipwebcam" / f"job{job.pk}_{timezone.now():%Y%m%d_%H%M%S}.mp4"
            capture_clip(job.camera_name, Path(settings.MEDIA_ROOT) / rel)
            job.video.name = str(rel)
            job.save(update_fields=["video"])
        result = predict_video(job.video.path)
    except (CaptureError, InferenceError) as exc:
        _fail(job, str(exc))
        return "FAILURE"
    except Exception as exc:                     # 예상 못 한 오류도 상태는 반드시 남긴다
        log.exception("analysis job %s failed", job_id)
        _fail(job, f"처리 중 오류가 발생했습니다: {type(exc).__name__}")
        return "FAILURE"

    with transaction.atomic():
        job.predictions.all().delete()
        PersonPrediction.objects.bulk_create([
            PersonPrediction(job=job, track_id=p["track_id"], action_id=p["action_id"],
                             action_label=p["action_label"], confidence=p["confidence"],
                             uncertain=p["uncertain"], window_count=p["window_count"],
                             valid_frames=p["valid_frames"], track_seconds=p["track_seconds"],
                             mean_keypoint_conf=p.get("mean_keypoint_conf"), top3=p.get("top3", []),
                             windows=p.get("windows", []))
            for p in result["predictions"]
        ])
        job.status = AnalysisJob.Status.SUCCESS
        job.result_message = result.get("message", "")[:200]
        job.video_seconds = result["video"]["seconds"]
        job.processing_seconds = result["processing_seconds"]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "result_message", "video_seconds", "processing_seconds", "finished_at"])
    return "SUCCESS"
