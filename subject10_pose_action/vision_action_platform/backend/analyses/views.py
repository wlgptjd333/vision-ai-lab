"""DRF API — /api/analyses/

  POST   /api/analyses/              분석 요청 → DB 저장 → (저장 확정 후) Celery 등록 → 작업 ID 즉시 반환(202)
  GET    /api/analyses/              내 분석 목록
  GET    /api/analyses/{id}/         상세 + 사람별 결과
  PATCH  /api/analyses/{id}/         제목·메모만 수정
  DELETE /api/analyses/{id}/         기록 삭제 (사람별 예측은 CASCADE, 영상 파일도 함께 지움)
  GET    /api/analyses/{id}/status/  상태만 (브라우저가 주기적으로 조회)
"""
import logging
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnalysisJob
from .permissions import IsOwner
from .serializers import (AnalysisJobCreateSerializer, AnalysisJobSerializer, AnalysisJobStatusSerializer,
                          AnalysisJobUpdateSerializer)
from .tasks import run_analysis

log = logging.getLogger(__name__)


class AnalysisJobViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]   # PUT(전체 수정) 막음

    def get_queryset(self):
        # 관리자도 API 에서는 본인 것만. 전체 관리는 Django Admin·/dashboard/ 에서 한다
        return AnalysisJob.objects.filter(user=self.request.user).prefetch_related("predictions")

    def get_serializer_class(self):
        if self.action == "create":
            return AnalysisJobCreateSerializer
        if self.action == "partial_update":
            return AnalysisJobUpdateSerializer
        if self.action == "status":
            return AnalysisJobStatusSerializer
        return AnalysisJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = str(uuid.uuid4())
        with transaction.atomic():
            job = serializer.save(user=request.user, celery_task_id=task_id)
            # DB 저장(commit)이 끝난 뒤에 작업을 등록 → Worker 가 아직 없는 행을 찾는 일이 없다
            transaction.on_commit(lambda: self._enqueue(job, task_id))
        job.refresh_from_db()
        return Response({"id": job.pk, "task_id": task_id, "status": job.status,
                         "status_url": f"/api/analyses/{job.pk}/status/"}, status=status.HTTP_202_ACCEPTED)

    @staticmethod
    def _enqueue(job, task_id):
        try:
            run_analysis.apply_async(args=[job.pk], task_id=task_id)
        except Exception as exc:                 # Redis 가 꺼져 있으면 기록만 남기고 실패로 표시
            log.exception("enqueue failed for job %s", job.pk)
            AnalysisJob.objects.filter(pk=job.pk).update(
                status=AnalysisJob.Status.FAILURE, finished_at=timezone.now(),
                error_message=f"작업 대기열(Redis)에 등록하지 못했습니다: {type(exc).__name__}")

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        super().update(request, *args, **kwargs)
        return Response(AnalysisJobSerializer(self.get_object()).data)

    def perform_destroy(self, instance):
        video = instance.video
        instance.delete()                        # PersonPrediction 은 on_delete=CASCADE 로 함께 삭제
        if video:
            video.delete(save=False)             # Media 폴더의 영상 파일도 지움

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        return Response(AnalysisJobStatusSerializer(self.get_object()).data)
