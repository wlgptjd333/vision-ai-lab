"""Docker 로 띄운 서비스를 브라우저와 같은 경로(세션 로그인 → DRF API)로 확인한다.

  python scripts/e2e_check.py <영상.mp4> [<영상2.mp4> ...]

.env 의 DEMO_* 계정을 쓴다. 확인 항목: T02 업로드, T05 즉시 반환, T06 저장, T07 다른 회원 접근, T09 잘못된 파일, T08 대시보드.
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8100")
ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def login(username: str, password: str) -> requests.Session:
    s = requests.Session()
    s.get(f"{BASE}/accounts/login/")
    r = s.post(f"{BASE}/accounts/login/", data={"username": username, "password": password,
                                                "csrfmiddlewaretoken": s.cookies["csrftoken"]},
               headers={"Referer": f"{BASE}/accounts/login/"}, allow_redirects=False)
    assert r.status_code == 302, f"login failed for {username}: {r.status_code}"
    s.headers["X-CSRFToken"] = s.cookies["csrftoken"]
    s.headers["Referer"] = BASE + "/"
    return s


def submit(s: requests.Session, path: str, expected: str = "") -> dict:
    t0 = time.perf_counter()
    with open(path, "rb") as f:
        r = s.post(f"{BASE}/api/analyses/", files={"video": (Path(path).name, f, "video/mp4")},
                   data={"input_type": "UPLOAD", "expected_action": expected, "title": Path(path).stem})
    return {"status_code": r.status_code, "seconds": round(time.perf_counter() - t0, 2), "body": r.json()}


def wait(s: requests.Session, job_id: int, limit: float = 600) -> dict:
    seen, t0 = [], time.perf_counter()
    while time.perf_counter() - t0 < limit:
        st = s.get(f"{BASE}/api/analyses/{job_id}/status/").json()
        if not seen or seen[-1] != st["status"]:
            seen.append(st["status"])
        if st["is_finished"]:
            break
        time.sleep(1)
    job = s.get(f"{BASE}/api/analyses/{job_id}/").json()
    job["_seen"] = seen
    return job


def main() -> None:
    env = load_env()
    a = login(env["DEMO_USER_A"], env["DEMO_USER_PASSWORD"])
    b = login(env["DEMO_USER_B"], env["DEMO_USER_PASSWORD"])
    ids = []
    for p in sys.argv[1:]:
        name = Path(p).stem
        m = re.search(r"_(A\d{3})_", name)                              # S03_A001_T01 → A001
        expected = m.group(1) if m else ""
        sub = submit(a, p, expected)
        print(f"[T05] POST {Path(p).name}: HTTP {sub['status_code']} in {sub['seconds']}s → {sub['body']}")
        job = wait(a, sub["body"]["id"])
        ids.append(job["id"])
        print(f"[T02] job {job['id']} 상태 흐름 {' → '.join(job['_seen'])} · AI {job['processing_seconds']}s "
              f"(영상 {job['video_seconds']}s) {job['error_message'] or job['result_message']}")
        for pr in job["predictions"]:
            mark = ("일치" if pr["action_id"] == expected else "불일치") if expected else "정답 없음"
            print(f"      track {pr['track_id']}: {pr['action_id']} {pr['action_name_ko']} {pr['confidence']:.2f}"
                  f"{' (불확실)' if pr['uncertain'] else ''} · 수행 {expected} → {mark}")

    bad = ROOT / "scripts" / "_broken.mp4"
    bad.write_bytes(b"this is not a video")
    sub = submit(a, str(bad))
    job = wait(a, sub["body"]["id"])
    bad.unlink()
    ids.append(job["id"])
    print(f"[T09] 손상 파일: HTTP {sub['status_code']} → {job['status']} · {job['error_message']}")
    r = a.post(f"{BASE}/api/analyses/", data={"input_type": "UPLOAD"}, files={"video": ("note.txt", b"x")})
    print(f"[T09] 잘못된 확장자: HTTP {r.status_code} {r.json()}")

    if ids:
        url = f"{BASE}/api/analyses/{ids[0]}/"
        codes = (b.get(url).status_code, b.patch(url, json={"title": "x"}).status_code, b.delete(url).status_code)
        print(f"[T07] B 가 A 의 작업 조회/수정/삭제: {codes} · B 목록 {b.get(BASE + '/api/analyses/').json()['count']}건")
        r = a.patch(url, json={"memo": "e2e 확인", "status": "FAILURE"})
        print(f"[T07] A PATCH 메모: HTTP {r.status_code} · 상태 그대로 {r.json()['status']} · PUT {a.put(url, json={}).status_code}")
    adm = login(env["DEMO_ADMIN_USERNAME"], env["DEMO_ADMIN_PASSWORD"])
    print(f"[T08] /dashboard/ 관리자 {adm.get(BASE + '/dashboard/').status_code} · 일반 회원 "
          f"{a.get(BASE + '/dashboard/', allow_redirects=False).status_code}")


if __name__ == "__main__":
    main()
