from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .actions import ACTION_BY_ID
from .models import AnalysisJob, PersonPrediction


class PersonPredictionSerializer(serializers.ModelSerializer):
    action_name_ko = serializers.SerializerMethodField()

    class Meta:
        model = PersonPrediction
        fields = ["track_id", "action_id", "action_label", "action_name_ko", "confidence",
                  "uncertain", "window_count", "valid_frames", "track_seconds", "mean_keypoint_conf",
                  "top3", "windows", "predicted_at"]

    def get_action_name_ko(self, obj):
        return ACTION_BY_ID.get(obj.action_id, {}).get("name_ko", "")


class AnalysisJobSerializer(serializers.ModelSerializer):
    """조회용. 상태·결과·오류는 모두 읽기 전용 — 사용자는 제목·메모만 바꿀 수 있다."""

    input_type_display = serializers.CharField(source="get_input_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    expected_action_display = serializers.CharField(source="get_expected_action_display", read_only=True)
    video_name = serializers.SerializerMethodField()
    predictions = PersonPredictionSerializer(many=True, read_only=True)
    is_finished = serializers.BooleanField(read_only=True)

    class Meta:
        model = AnalysisJob
        fields = ["id", "title", "memo", "input_type", "input_type_display", "video_name", "camera_name",
                  "expected_action", "expected_action_display", "status", "status_display", "is_finished",
                  "celery_task_id", "error_message", "result_message", "video_seconds", "processing_seconds",
                  "created_at", "started_at", "finished_at", "predictions"]
        read_only_fields = [f for f in fields if f not in {"title", "memo"}]

    def get_video_name(self, obj):
        return Path(obj.video.name).name if obj.video else ""


class AnalysisJobCreateSerializer(serializers.ModelSerializer):
    """분석 요청 입력 검사: 업로드는 영상 파일, IP Webcam 은 허용 목록에 있는 카메라 이름만."""

    class Meta:
        model = AnalysisJob
        fields = ["input_type", "video", "camera_name", "expected_action", "title", "memo"]

    def validate(self, attrs):
        kind = attrs.get("input_type")
        if kind == AnalysisJob.InputType.UPLOAD:
            video = attrs.get("video")
            if not video:
                raise serializers.ValidationError({"video": "분석할 영상 파일을 선택하세요."})
            ext = Path(video.name).suffix.lower()
            if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
                raise serializers.ValidationError(
                    {"video": f"영상 파일만 올릴 수 있습니다 ({', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)})."})
            if video.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise serializers.ValidationError({"video": f"{settings.MAX_UPLOAD_MB} MB 이하 영상만 올릴 수 있습니다."})
            attrs["camera_name"] = ""
        elif kind == AnalysisJob.InputType.IPWEBCAM:
            name = attrs.get("camera_name", "")
            if name not in settings.IPWEBCAM_CAMERAS:
                allowed = ", ".join(settings.IPWEBCAM_CAMERAS) or "없음 (.env 의 IPWEBCAM_CAMERAS 확인)"
                raise serializers.ValidationError({"camera_name": f"허용된 카메라만 쓸 수 있습니다. 허용 목록: {allowed}"})
            attrs.pop("video", None)
        return attrs


class AnalysisJobUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisJob
        fields = ["title", "memo"]


class AnalysisJobStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_finished = serializers.BooleanField(read_only=True)
    prediction_count = serializers.IntegerField(source="predictions.count", read_only=True)

    class Meta:
        model = AnalysisJob
        fields = ["id", "status", "status_display", "is_finished", "error_message", "result_message",
                  "prediction_count", "started_at", "finished_at"]
