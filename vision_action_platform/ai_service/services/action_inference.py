"""사람별 Frame Feature → 30단계 Sequence → Random Forest → Track ID 별 Action·Confidence.

창(Window) 규칙
  - 6일차 모델은 Clip 전체(2.5~10.7초)를 30단계로 편 값으로 학습했다.
    7일차 실시간은 최근 5초를 봤지만, 5초 창으로 S03 Test 6개를 돌리면 5초보다 긴 2개(A003 10.7초,
    A004 5.4초)가 동작이 잘려 틀렸다 (4/6). 그래서 창을 가장 긴 학습 Clip보다 조금 긴 12초로 둔다 (6/6).
  - 사람이 12초 이하로 보이면 그 전체를 창 하나로 본다 (학습과 같은 모양).
    더 길면 12초 창을 4초씩 밀며 여러 개 만들고, 창별 확률을 평균해 사람 한 명의 결과로 정한다.
  - 창이 준비됐는지 판단은 7일차 ActionWindowBuffer.is_ready 와 같다:
      창 시간이 창 길이 × 0.8 이상(짧은 Track 하나짜리 창은 제외) · 유효 Frame 비율 0.6 이상 · 10개 이상
  - 7일차 Stabilizer(최근 5번 중 3표)는 '화면에 지금 뭘 띄울지'용이라, 영상 전체 결과에는 평균을 쓴다.
  - 평균 확률 1위가 0.25 미만이면 '판단 불확실'. 7일차 0.55를 그대로 쓰면 6개 Clip으로 학습한 이 모델은
    모든 결과가 불확실이 된다 (최고 0.37). 0.25는 Val(S02)에서 정했다: 맞힌 3개 0.30~0.32, 틀린 3개 0.21~0.23.

30단계 변환은 수업 코드 src/sequence_utils.resample_sequence 를 그대로 쓴다 (학습 34번과 같은 함수).
"""
from __future__ import annotations

import numpy as np

from services.pose_pipeline import TrackData
from src.sequence_utils import flatten_sequence, resample_sequence


def make_windows(t_start: float, t_end: float, size: float, stride: float) -> list[tuple[float, float]]:
    if t_end - t_start <= size:
        return [(t_start, t_end)]
    starts = list(np.arange(t_start, t_end - size, stride))
    starts.append(t_end - size)                      # 마지막 창은 끝에 맞춤
    return [(float(s), float(s) + size) for s in starts]


def window_ready(span: float, n_all: int, n_valid: int, cfg: dict, short_track: bool) -> bool:
    if not short_track and span < cfg["window_seconds"] * cfg["min_window_fill_ratio"]:
        return False
    if n_valid / max(n_all, 1) < cfg["min_valid_feature_ratio"]:
        return False
    return n_valid >= cfg["min_valid_features"]


def predict_track(track: TrackData, bundle) -> dict:
    cfg, steps = bundle.config, bundle.info["sequence_steps"]
    times = np.asarray(track.times, dtype=float)
    valid = np.asarray(track.valid, dtype=bool)
    span = float(times[-1] - times[0]) if len(times) > 1 else 0.0
    quality = {"frames": int(len(times)), "valid_frames": int(valid.sum()),
               "valid_ratio": round(float(valid.mean()), 3) if len(valid) else 0.0,
               "track_seconds": round(span, 2),
               "mean_keypoint_conf": round(float(np.mean(track.keypoint_conf)), 3)}
    if span < cfg["min_track_seconds"]:
        return {"skipped": True, "reason": f"화면에 {span:.1f}초만 보여 판단하지 않음", **quality}

    short = span <= cfg["window_seconds"]
    probs, windows = [], []
    for s, e in make_windows(float(times[0]), float(times[-1]), cfg["window_seconds"], cfg["window_stride_seconds"]):
        m = (times >= s - 1e-9) & (times <= e + 1e-9)
        idx = np.flatnonzero(m & valid)
        n_all, n_valid = int(m.sum()), len(idx)
        win_span = float(times[m][-1] - times[m][0]) if n_all > 1 else 0.0
        if not window_ready(win_span, n_all, n_valid, cfg, short):
            continue
        feats = np.stack([track.features[i] for i in idx])
        seq = resample_sequence(feats, times[idx], target_steps=steps)
        p = bundle.model.predict_proba(flatten_sequence(seq).reshape(1, -1))[0]
        probs.append(p)
        k = int(np.argmax(p))
        windows.append({"start_sec": round(s, 2), "end_sec": round(e, 2),
                        "action_id": bundle.actions[bundle.classes[k]]["action_id"],
                        "confidence": round(float(p[k]), 4)})
    if not probs:
        return {"skipped": True,
                "reason": "관절이 잘 보이는 Frame 이 부족함 (창마다 유효 Frame 10개·60% 미만)",
                **quality}

    mean_p = np.mean(probs, axis=0)
    order = np.argsort(mean_p)[::-1]

    def describe(i: int) -> dict:
        a = bundle.actions[bundle.classes[i]]
        return {"action_id": a["action_id"], "action_label": a["label"], "action_name_ko": a["name_ko"],
                "probability": round(float(mean_p[i]), 4)}

    best = describe(int(order[0]))
    return {
        "skipped": False,
        "action_id": best["action_id"],
        "action_label": best["action_label"],
        "action_name_ko": best["action_name_ko"],
        "confidence": best["probability"],
        "uncertain": best["probability"] < cfg["uncertain_below"],
        "window_count": len(probs),
        "top3": [describe(int(i)) for i in order[:3]],
        "windows": windows,
        **quality,
    }


def predict_tracks(video, bundle) -> tuple[list[dict], list[dict]]:
    """(predictions, skipped). Track ID 순서로 정렬."""
    preds, skipped = [], []
    for tid in sorted(video.tracks):
        r = predict_track(video.tracks[tid], bundle)
        (skipped if r.pop("skipped") else preds).append({"track_id": tid, **r})
    return preds, skipped
