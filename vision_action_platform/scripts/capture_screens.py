"""README 용 화면 캡처 (Playwright, 헤드리스 Chromium). 비밀번호·카메라 주소는 화면에 나오지 않는다.

  pip install playwright && playwright install chromium
  python scripts/capture_screens.py --success 5 --failure 4 --multi 7
결과: docs/images/screen_*.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from e2e_check import BASE, load_env

OUT = Path(__file__).resolve().parents[1] / "docs" / "images"


def login(page, user, pw):
    page.goto(f"{BASE}/accounts/login/")
    page.fill("input[name=username]", user)
    page.fill("input[name=password]", pw)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def shot(page, url, name, wait="networkidle", full=True, before=None):
    page.goto(BASE + url)
    page.wait_for_load_state(wait)
    if before:
        before(page)
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / name), full_page=full)
    print("saved", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--success", type=int, required=True)
    ap.add_argument("--failure", type=int, required=True)
    ap.add_argument("--multi", type=int)
    ap.add_argument("--channel", default=None, help="설치된 브라우저 사용 (예: msedge, chrome)")
    a = ap.parse_args()
    env = load_env()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel=a.channel) if a.channel else p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 860}, device_scale_factor=1, locale="ko-KR",
                            color_scheme="light")
        page = ctx.new_page()
        login(page, env["DEMO_USER_A"], env["DEMO_USER_PASSWORD"])
        shot(page, "/", "screen_index_upload.png")
        shot(page, "/", "screen_index_ipwebcam.png", full=False,
             before=lambda pg: pg.click("button[data-input=IPWEBCAM]"))
        shot(page, f"/analyses/{a.success}/", "screen_result_success.png")
        shot(page, f"/analyses/{a.failure}/", "screen_result_failure.png")
        if a.multi:
            shot(page, f"/analyses/{a.multi}/", "screen_result_two_people.png")
        page.goto(f"{BASE}/dashboard/")
        print("normal user /dashboard/ ->", page.url)
        ctx.clear_cookies()
        login(page, env["DEMO_ADMIN_USERNAME"], env["DEMO_ADMIN_PASSWORD"])
        shot(page, "/dashboard/", "screen_dashboard.png")
        shot(page, "/admin/analyses/analysisjob/", "screen_admin_jobs.png", full=False)
        b.close()


if __name__ == "__main__":
    main()
