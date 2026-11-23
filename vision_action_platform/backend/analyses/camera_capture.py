"""허용된 IP Webcam 에서 정해진 시간(기본 8초)만 Frame 을 읽어 MP4 로 저장하고 끝낸다.

  - 카메라 주소는 .env 의 IPWEBCAM_CAMERAS 에만 있고, 사용자는 이름만 고른다 (임의 URL 호출 방지)
  - 연결이 안 되거나 중간에 끊기면 CaptureError → 작업은 FAILURE 와 사유로 저장
"""
import time
from pathlib import Path

import cv2
from django.conf import settings


class CaptureError(Exception):
    pass


def capture_clip(camera_name: str, out_path: Path, seconds: float | None = None) -> dict:
    url = settings.IPWEBCAM_CAMERAS.get(camera_name)
    if not url:
        raise CaptureError(f"허용되지 않은 카메라입니다: {camera_name}")
    seconds = seconds or settings.CAPTURE_SECONDS
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.CAPTURE_CONNECT_TIMEOUT_SECONDS * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
    if not cap.isOpened():
        raise CaptureError(f"카메라 '{camera_name}'에 연결하지 못했습니다. 휴대폰 IP Webcam 앱이 켜져 있고 같은 네트워크인지 확인하세요.")
    ok, frame = cap.read()
    if not ok:
        cap.release()
        raise CaptureError(f"카메라 '{camera_name}'에서 화면을 받지 못했습니다.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = frame.shape[:2]
    frames, misses = [frame], 0
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        ok, frame = cap.read()
        if not ok:
            misses += 1
            if misses > 30:
                break
            continue
        frames.append(frame)
    cap.release()
    elapsed = time.monotonic() - start
    if elapsed < seconds * 0.5 or len(frames) < 10:
        raise CaptureError(f"카메라 연결이 중간에 끊겼습니다 ({elapsed:.1f}초 / {len(frames)} Frame 수집).")

    # 휴대폰 스트림은 FPS 표시가 부정확해 실제로 받은 Frame 수 / 시간으로 저장한다
    fps = max(1.0, len(frames) / elapsed)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        writer.write(f)
    writer.release()
    return {"frames": len(frames), "seconds": round(elapsed, 2), "fps": round(fps, 2), "width": w, "height": h}
