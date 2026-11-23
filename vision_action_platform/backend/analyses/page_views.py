"""HTML 화면. 데이터는 JavaScript(analyses.js)가 DRF API 로 가져오고, 대시보드는 ORM 집계 결과를 Template 에 넘긴다."""
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render

from .actions import ACTIONS
from .models import AnalysisJob, PersonPrediction
from .services import health


def _page_context():
    return {
        "actions": ACTIONS,
        "cameras": list(settings.IPWEBCAM_CAMERAS),          # 이름만 (주소는 화면에 보내지 않음)
        "capture_seconds": settings.CAPTURE_SECONDS,
        "uncertain_below": settings.UNCERTAIN_BELOW,
        "max_upload_mb": settings.MAX_UPLOAD_MB,
    }


@login_required
def index(request):
    return render(request, "analyses/index.html", _page_context())


@login_required
def detail(request, pk):
    job = get_object_or_404(AnalysisJob, pk=pk, user=request.user)
    return render(request, "analyses/detail.html", {**_page_context(), "job": job})


@staff_member_required
def dashboard(request):
    # ① 동작별 예측 건수 — 한 번도 안 나온 동작도 0 으로 보여 준다
    by_action = dict(PersonPrediction.objects.values_list("action_id").annotate(n=Count("id")))
    uncertain = dict(PersonPrediction.objects.filter(uncertain=True)
                     .values_list("action_id").annotate(n=Count("id")))
    action_rows = [{"id": a[0], "name_ko": a[2],
                    "count": by_action.get(a[0], 0), "uncertain": uncertain.get(a[0], 0)} for a in ACTIONS]
    # ② 작업 상태별 건수
    by_status = dict(AnalysisJob.objects.values_list("status").annotate(n=Count("id")))
    status_rows = [{"status": s.value, "label": s.label, "count": by_status.get(s.value, 0)}
                   for s in AnalysisJob.Status]
    # 선택: 입력 방식별 건수·평균 처리 시간
    by_input = {r["input_type"]: r for r in AnalysisJob.objects.values("input_type").annotate(
        n=Count("id"), avg_sec=Avg("processing_seconds"))}
    input_rows = [{"type": t.value, "label": t.label, "count": by_input.get(t.value, {}).get("n", 0),
                   "avg_seconds": round(by_input.get(t.value, {}).get("avg_sec") or 0, 2)}
                  for t in AnalysisJob.InputType]
    chart_data = {"actions": action_rows, "statuses": status_rows, "inputs": input_rows}
    summary = {
        "jobs": AnalysisJob.objects.count(),
        "users": AnalysisJob.objects.values("user").distinct().count(),
        "predictions": PersonPrediction.objects.count(),
        "uncertain": PersonPrediction.objects.filter(uncertain=True).count(),
    }
    recent = AnalysisJob.objects.select_related("user").prefetch_related("predictions")[:10]
    return render(request, "analyses/dashboard.html",
                  {"chart_data": chart_data, "summary": summary, "recent": recent, "ai_health": health()})
