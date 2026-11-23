from django.contrib import admin

from .models import AnalysisJob, PersonPrediction


class PersonPredictionInline(admin.TabularInline):
    model = PersonPrediction
    extra = 0
    can_delete = False
    fields = ["track_id", "action_id", "action_label", "confidence", "uncertain", "window_count", "valid_frames",
              "track_seconds"]
    readonly_fields = fields


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "input_type", "status", "expected_action", "prediction_summary",
                    "processing_seconds", "created_at"]
    list_filter = ["status", "input_type", "expected_action", "created_at"]
    search_fields = ["user__username", "title", "memo", "celery_task_id"]
    readonly_fields = ["celery_task_id", "status", "error_message", "result_message", "video_seconds",
                       "processing_seconds", "created_at", "started_at", "finished_at"]
    inlines = [PersonPredictionInline]
    date_hierarchy = "created_at"

    @admin.display(description="사람별 예측")
    def prediction_summary(self, obj):
        return ", ".join(f"#{p.track_id} {p.action_id} {p.confidence:.2f}" for p in obj.predictions.all()) or "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user").prefetch_related("predictions")


@admin.register(PersonPrediction)
class PersonPredictionAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "track_id", "action_id", "action_label", "confidence", "uncertain", "window_count",
                    "predicted_at"]
    list_filter = ["action_id", "uncertain", "job__input_type"]
    search_fields = ["job__user__username", "action_label"]
    readonly_fields = [f.name for f in PersonPrediction._meta.fields]
