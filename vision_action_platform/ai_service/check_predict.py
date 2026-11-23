"""T01·추론 확인용: 서버를 띄우지 않고 FastAPI 앱에 영상 몇 개를 보내 본다.

  .venv/bin/python check_predict.py <영상1.mp4> [<영상2.mp4> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

with TestClient(app) as client:
    h = client.get("/health").json()
    m = h["model"]
    print(f"health: {h['status']} · device {h['device']} · {m['n_classes']} classes · {m['n_features']} features "
          f"({m['sequence_steps']} steps × {m['frame_features']}) · window {m['window_seconds']}s · {m['error']}")
    for p in sys.argv[1:]:
        with open(p, "rb") as f:
            r = client.post("/predict/video", files={"file": (Path(p).name, f, "video/mp4")})
        if r.status_code != 200:
            print(f"{Path(p).name}: HTTP {r.status_code} {r.json()}")
            continue
        j = r.json()
        print(f"{Path(p).name}: {j['video']['seconds']}s {j['video']['width']}x{j['video']['height']} · "
              f"{j['processing_seconds']}s · {j['message'] or 'OK'}")
        for pr in j["predictions"]:
            top = ", ".join(f"{t['action_id']} {t['probability']:.2f}" for t in pr["top3"])
            print(f"   track {pr['track_id']}: {pr['action_id']} {pr['action_label']} ({pr['action_name_ko']}) "
                  f"conf {pr['confidence']:.2f}{' 불확실' if pr['uncertain'] else ''} · windows {pr['window_count']} · "
                  f"valid {pr['valid_frames']}/{pr['frames']} · top3 [{top}]")
        for s in j["skipped_tracks"]:
            print(f"   track {s['track_id']} skipped: {s['reason']}")
