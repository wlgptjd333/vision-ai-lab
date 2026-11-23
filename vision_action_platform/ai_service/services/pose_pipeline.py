"""영상 → YOLO Pose + ByteTrack → 사람(Track ID)별 Frame Feature 목록.

Frame 하나의 Feature 는 수업 코드(src/multi_person_utils.feature_from_keypoints)를 그대로 쓴다.
  38개 = 어깨 폭으로 정규화한 17관절 x,y (34) + 팔꿈치·무릎 각도 (4)
어깨 폭 정규화가 안 되거나 값에 NaN 이 있으면 None → 그 Frame 은 '무효'로 센다 (8일차와 같음).

6일차 학습 영상은 한 명씩 찍었지만, 서비스에서는 8일차처럼 ByteTrack 으로
사람마다 Track ID 를 붙여 사람별로 따로 모은다.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from src.multi_person_utils import feature_from_keypoints

# YOLO 모델·Tracker 는 요청끼리 공유하면 Track ID 가 섞이므로 영상 한 건씩 처리한다
_TRACK_LOCK = threading.Lock()


class VideoReadError(Exception):
    """영상 파일을 열 수 없거나 Frame 이 없음 → 400 응답"""


@dataclass
class TrackData:
    times: list[float] = field(default_factory=list)
    features: list[np.ndarray | None] = field(default_factory=list)
    keypoint_conf: list[float] = field(default_factory=list)

    @property
    def valid(self) -> list[bool]:
        return [f is not None for f in self.features]


@dataclass
class VideoResult:
    tracks: dict[int, TrackData]
    frames: int
    fps: float
    width: int
    height: int
    pose_seconds: float

    @property
    def seconds(self) -> float:
        return round(self.frames / self.fps, 2) if self.fps else 0.0


def extract_tracks(video_path: str, pose_model, cfg: dict, device) -> VideoResult:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise VideoReadError("영상 파일을 열 수 없습니다. MP4 등 정상적인 영상인지 확인하세요.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    if not fps or fps != fps or fps > 240:
        fps = 30.0
    max_frames = int(cfg["max_video_seconds"] * fps)
    # 60fps 영상은 2 Frame 마다 1개만 처리 (30단계로 보간하므로 결과 영향은 작고 처리 시간은 절반)
    step = max(1, round(fps / cfg.get("max_process_fps", 30)))
    tracks: dict[int, TrackData] = {}
    n, used, w, h = 0, 0, 0, 0
    t0 = time.perf_counter()
    with _TRACK_LOCK:
        while n < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            n += 1
            if (n - 1) % step:
                continue
            used += 1
            h, w = frame.shape[:2]
            result = pose_model.track(source=frame, persist=used > 1, tracker=cfg["tracker"],
                                      imgsz=cfg["image_size"], conf=cfg["person_confidence"],
                                      device=device, verbose=False)[0]
            boxes, kps = result.boxes, result.keypoints
            if boxes is None or boxes.id is None or kps is None or kps.xy is None:
                continue
            ids = boxes.id.int().cpu().tolist()
            xys = kps.xy.cpu().numpy()
            confs = kps.conf.cpu().numpy() if kps.conf is not None else np.ones((len(ids), 17), np.float32)
            t = (n - 1) / fps
            for tid, xy, conf in zip(ids, xys, confs):
                tr = tracks.setdefault(int(tid), TrackData())
                tr.times.append(t)
                tr.features.append(feature_from_keypoints(xy))
                tr.keypoint_conf.append(float(np.mean(conf)))
    cap.release()
    if n == 0:
        raise VideoReadError("영상에서 Frame 을 읽지 못했습니다. 파일이 손상됐거나 지원하지 않는 형식입니다.")
    return VideoResult(tracks=tracks, frames=n, fps=round(fps, 3), width=w, height=h,
                       pose_seconds=round(time.perf_counter() - t0, 2))
