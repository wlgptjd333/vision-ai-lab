"""과제 테스트 중 서버 없이 확인할 수 있는 것 (T02·T04·T05·T06·T07·T08·T09 일부).

FastAPI 와 카메라는 가짜(mock)로 바꾸고, Celery 작업은 on_commit 콜백을 직접 실행해 같은 흐름을 탄다.
실제 서버·Docker 를 거친 확인은 README 의 테스트 표에 따로 기록한다.
"""
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .camera_capture import CaptureError
from .models import AnalysisJob, PersonPrediction
from .services import InferenceError
from .tasks import run_analysis

TMP_MEDIA = tempfile.mkdtemp()


def fake_result(n_people=2):
    preds = [{"track_id": i + 1, "action_id": aid, "action_label": label, "action_name_ko": "x", "confidence": conf,
              "uncertain": conf < 0.25, "window_count": 1, "valid_frames": 150, "track_seconds": 5.0,
              "mean_keypoint_conf": 0.9, "top3": [{"action_id": aid, "probability": conf}], "windows": []}
             for i, (aid, label, conf) in enumerate([("A001", "bend_return", 0.37), ("A006", "wave", 0.21)][:n_people])]
    return {"ok": True, "message": "" if preds else "영상에서 사람을 찾지 못했습니다.",
            "video": {"seconds": 5.2, "frames": 156}, "processing_seconds": 3.1, "predictions": preds}


def video_file(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42fake", content_type="video/mp4")


@override_settings(MEDIA_ROOT=TMP_MEDIA, IPWEBCAM_CAMERAS={"phone": "http://192.0.2.10:8080/video"})
class AnalysisApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.a = User.objects.create_user("user_a", password="pw-A-12345")
        self.b = User.objects.create_user("user_b", password="pw-B-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.a)

    def create(self, data, result=None, error=None):
        """POST 후 transaction.on_commit 으로 등록된 Celery 작업을 그 자리에서 실행"""
        side = error if error else None
        with mock.patch("analyses.tasks.predict_video", return_value=result or fake_result(),
                        side_effect=side) as pv, \
                mock.patch("analyses.views.run_analysis.apply_async",
                           side_effect=lambda args, task_id: run_analysis(*args)):
            with self.captureOnCommitCallbacks(execute=True):
                r = self.api.post("/api/analyses/", data, format="multipart")
        return r, pv

    # T02·T05: 업로드 → 작업 ID 즉시 반환(202) → Worker 가 결과 저장
    def test_upload_returns_job_id_and_saves_result(self):
        r, pv = self.create({"input_type": "UPLOAD", "video": video_file(), "expected_action": "A001"})
        self.assertEqual(r.status_code, 202)
        self.assertIn("task_id", r.data)
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual(job.status, "SUCCESS")
        self.assertEqual(job.celery_task_id, r.data["task_id"])
        self.assertEqual(job.user, self.a)
        pv.assert_called_once()

    # T04: 두 사람 → 한 작업에 Track ID 별 결과 2개
    def test_two_people_saved_separately(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()})
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual(list(job.predictions.values_list("track_id", "action_id")), [(1, "A001"), (2, "A006")])
        self.assertTrue(job.predictions.get(track_id=2).uncertain)

    # T06: 새로 조회해도(새로고침) 같은 결과
    def test_result_persists_in_detail_and_status(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()})
        d = self.api.get(f"/api/analyses/{r.data['id']}/").data
        self.assertEqual(len(d["predictions"]), 2)
        s = self.api.get(f"/api/analyses/{r.data['id']}/status/").data
        self.assertEqual((s["status"], s["is_finished"], s["prediction_count"]), ("SUCCESS", True, 2))

    def test_no_person_is_success_with_message(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()}, result=fake_result(0))
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual((job.status, job.predictions.count()), ("SUCCESS", 0))
        self.assertIn("사람", job.result_message)

    # T09: 잘못된 파일 · AI 서버 오류 · 카메라 끊김
    def test_wrong_extension_rejected(self):
        r, pv = self.create({"input_type": "UPLOAD", "video": SimpleUploadedFile("a.txt", b"hello")})
        self.assertEqual(r.status_code, 400)
        self.assertIn("video", r.data)
        pv.assert_not_called()

    def test_inference_error_saved_as_failure(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()},
                           error=InferenceError("AI 서버 오류 (400): 영상 파일을 열 수 없습니다."))
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual(job.status, "FAILURE")
        self.assertIn("열 수 없습니다", job.error_message)
        self.assertIsNotNone(job.finished_at)

    def test_queue_down_saved_as_failure(self):
        with mock.patch("analyses.views.run_analysis.apply_async", side_effect=ConnectionError("redis down")):
            with self.captureOnCommitCallbacks(execute=True):
                r = self.api.post("/api/analyses/", {"input_type": "UPLOAD", "video": video_file()}, format="multipart")
        self.assertEqual(r.status_code, 202)
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual(job.status, "FAILURE")
        self.assertIn("Redis", job.error_message)

    def test_ipwebcam_only_allowed_camera(self):
        r, _ = self.create({"input_type": "IPWEBCAM", "camera_name": "http://evil.example/video"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("camera_name", r.data)

    def test_ipwebcam_disconnect_saved_as_failure(self):
        with mock.patch("analyses.tasks.capture_clip", side_effect=CaptureError("카메라 'phone'에 연결하지 못했습니다.")):
            r, pv = self.create({"input_type": "IPWEBCAM", "camera_name": "phone"})
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual((job.status, job.input_type), ("FAILURE", "IPWEBCAM"))
        self.assertIn("연결하지 못했습니다", job.error_message)
        pv.assert_not_called()

    # T07: B 는 A 의 기록을 조회·수정·삭제할 수 없음
    def test_other_user_cannot_access(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()})
        url = f"/api/analyses/{r.data['id']}/"
        other = APIClient()
        other.force_authenticate(self.b)
        self.assertEqual(other.get(url).status_code, 404)
        self.assertEqual(other.patch(url, {"title": "hack"}).status_code, 404)
        self.assertEqual(other.delete(url).status_code, 404)
        self.assertEqual(other.get(url + "status/").status_code, 404)
        self.assertEqual(other.get("/api/analyses/").data["count"], 0)
        self.assertTrue(AnalysisJob.objects.filter(pk=r.data["id"]).exists())

    def test_patch_changes_only_title_and_memo(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()})
        url = f"/api/analyses/{r.data['id']}/"
        res = self.api.patch(url, {"title": "1차 시연", "memo": "정면", "status": "FAILURE"}, format="json")
        self.assertEqual(res.status_code, 200)
        job = AnalysisJob.objects.get(pk=r.data["id"])
        self.assertEqual((job.title, job.memo, job.status), ("1차 시연", "정면", "SUCCESS"))
        self.assertEqual(self.api.put(url, {"title": "x"}, format="json").status_code, 405)

    def test_delete_removes_predictions_and_file(self):
        r, _ = self.create({"input_type": "UPLOAD", "video": video_file()})
        job = AnalysisJob.objects.get(pk=r.data["id"])
        storage, name = job.video.storage, job.video.name
        self.assertTrue(storage.exists(name))
        self.assertEqual(self.api.delete(f"/api/analyses/{job.pk}/").status_code, 204)
        self.assertFalse(PersonPrediction.objects.filter(job_id=job.pk).exists())
        self.assertFalse(storage.exists(name))


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class DashboardTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss", password="pw-boss-123", is_staff=True)
        self.user = User.objects.create_user("normal", password="pw-normal-123")
        job = AnalysisJob.objects.create(user=self.user, input_type="UPLOAD", status="SUCCESS")
        AnalysisJob.objects.create(user=self.user, input_type="IPWEBCAM", status="FAILURE")
        PersonPrediction.objects.create(job=job, track_id=1, action_id="A005", action_label="sit_stand",
                                        confidence=0.6, window_count=1)

    # T08: 관리자만 /dashboard/, 차트 2개용 ORM 집계
    @mock.patch("analyses.page_views.health", return_value={"status": "ok"})
    def test_dashboard_staff_only_with_aggregates(self, _):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/dashboard/").status_code, 302)
        self.client.force_login(self.staff)
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        data = r.context["chart_data"]
        self.assertEqual(len(data["actions"]), 6)
        self.assertEqual(next(a["count"] for a in data["actions"] if a["id"] == "A005"), 1)
        self.assertEqual({s["status"]: s["count"] for s in data["statuses"]},
                         {"PENDING": 0, "STARTED": 0, "SUCCESS": 1, "FAILURE": 1})

    def test_admin_lists_jobs_for_staff(self):
        self.staff.is_superuser = True
        self.staff.save()
        self.client.force_login(self.staff)
        r = self.client.get("/admin/analyses/analysisjob/?status__exact=FAILURE")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "IP Webcam")
