/* 분석 화면 (index.html · detail.html)
 * 흐름: AI 분석 시작 → POST /api/analyses/ (작업 ID 즉시 받음) → /status/ 를 2초마다 조회
 *       → 완료되면 상세 GET 으로 사람별 결과 표시 → 최근 이력 새로고침
 * 구성: Config · Util · Data(API) · View · Handlers · Init · Entry (수업 DRF 문제의 JS 구조와 같음)
 */
(function () {
  "use strict";

  // ── Config ──
  const Config = {
    api: "/api/analyses/",
    pollMs: 2000,
    pollLimit: 450,                       // 2초 × 450 = 15분 (Celery 시간 제한과 같음)
    statusKo: { PENDING: "대기", STARTED: "처리 중", SUCCESS: "완료", FAILURE: "실패" },
  };

  // ── Util ──
  const Util = {
    $(sel, root = document) { return root.querySelector(sel); },
    $$(sel, root = document) { return Array.from(root.querySelectorAll(sel)); },
    csrf() {
      const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : "";
    },
    esc(s) {
      return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    },
    pct(x) { return x == null ? "-" : `${(x * 100).toFixed(0)}%`; },
    sec(x) { return x == null ? "-" : `${Number(x).toFixed(1)}초`; },
    time(iso) {
      if (!iso) return "-";
      const d = new Date(iso);
      return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${d.toTimeString().slice(0, 5)}`;
    },
    errorText(err) {
      const data = err?.response?.data;
      if (!data) return "서버에 연결하지 못했습니다.";
      if (typeof data === "string") return data.slice(0, 200);
      return Object.values(data).flat().join(" ");
    },
    uncertainBelow() {
      const el = document.getElementById("uncertain-below");
      return el ? JSON.parse(el.textContent) : 0.3;
    },
  };

  // ── Data (DRF API) ──
  const http = axios.create({ headers: { "X-CSRFToken": Util.csrf() } });
  const Data = {
    create: (formData) => http.post(Config.api, formData).then((r) => r.data),
    list: () => http.get(Config.api).then((r) => r.data.results ?? r.data),
    detail: (id) => http.get(`${Config.api}${id}/`).then((r) => r.data),
    status: (id) => http.get(`${Config.api}${id}/status/`).then((r) => r.data),
    update: (id, body) => http.patch(`${Config.api}${id}/`, body).then((r) => r.data),
    remove: (id) => http.delete(`${Config.api}${id}/`),
  };

  // ── View ──
  const View = {
    badge(status) {
      return `<span class="badge s-${status}">${Config.statusKo[status] ?? status}</span>`;
    },
    predictionLine(p) {
      const flag = p.uncertain ? ' <span class="badge warn">판단 불확실</span>' : "";
      return `#${p.track_id} ${Util.esc(p.action_id)} ${Util.esc(p.action_name_ko)} ${Util.pct(p.confidence)}${flag}`;
    },
    resultTable(job) {
      if (job.status === "FAILURE") {
        return `<p class="error">실패 사유: ${Util.esc(job.error_message)}</p>`;
      }
      if (job.status !== "SUCCESS") return "";
      if (!job.predictions.length) {
        return `<p class="warn-text">${Util.esc(job.result_message || "예측 결과가 없습니다.")}</p>`;
      }
      const limit = Util.uncertainBelow();
      const rows = job.predictions.map((p) => {
        const match = job.expected_action
          ? (job.expected_action === p.action_id ? '<span class="badge ok">일치</span>' : '<span class="badge bad">불일치</span>')
          : "-";
        const top3 = p.top3.map((t) => `${Util.esc(t.action_id)} ${Util.esc(t.action_label)} ${Util.pct(t.probability)}`).join("<br>");
        return `<tr class="${p.uncertain ? "uncertain" : ""}">
          <td>#${p.track_id}</td>
          <td><strong>${Util.esc(p.action_id)} ${Util.esc(p.action_name_ko)}</strong><br><span class="muted">${Util.esc(p.action_label)}</span></td>
          <td><div class="bar"><span style="width:${(p.confidence * 100).toFixed(0)}%"></span></div>${Util.pct(p.confidence)}${p.uncertain ? '<br><span class="badge warn">판단 불확실</span>' : ""}</td>
          <td>${match}</td>
          <td class="small">${top3}</td>
          <td class="small">창 ${p.window_count}개<br>유효 Frame ${p.valid_frames}<br>${Util.sec(p.track_seconds)} 보임<br>관절 Conf ${p.mean_keypoint_conf ?? "-"}</td>
        </tr>`;
      }).join("");
      return `<table class="table">
        <thead><tr><th>Track</th><th>예측 동작</th><th>Confidence</th><th>수행한 동작과</th><th>상위 3개</th><th>입력 품질</th></tr></thead>
        <tbody>${rows}</tbody></table>
        <p class="muted small">Confidence ${Util.pct(limit)} 미만은 '판단 불확실'로 표시합니다. 6개 동작 중 하나를 고르는 모델이라(6개 중 무작위면 17%), 학습하지 않은 동작에도 가장 가까운 동작을 답합니다.</p>`;
    },
    steps(status) {
      const order = ["PENDING", "STARTED", "DONE"];
      const now = status === "SUCCESS" || status === "FAILURE" ? "DONE" : status;
      Util.$$("#status-steps li").forEach((li) => {
        const i = order.indexOf(li.dataset.step);
        li.className = i < order.indexOf(now) ? "done" : i === order.indexOf(now) ? `now s-${status}` : "";
      });
    },
    current(job) {
      Util.$("#current").hidden = false;
      Util.$("#current-id").innerHTML = `#${job.id} ${View.badge(job.status)}`;
      View.steps(job.status);
      const msg = { PENDING: "작업을 대기열에 넣었습니다.", STARTED: "AI 서버가 영상을 분석하고 있습니다…" }[job.status];
      Util.$("#current-message").textContent = msg ?? (job.processing_seconds ? `AI 처리 ${Util.sec(job.processing_seconds)} · 영상 ${Util.sec(job.video_seconds)}` : "");
      Util.$("#current-result").innerHTML = job.predictions ? View.resultTable(job) + `<p><a href="/analyses/${job.id}/">상세 보기 →</a></p>` : "";
    },
    history(jobs) {
      const body = Util.$("#history tbody");
      if (!body) return;
      body.innerHTML = jobs.length ? jobs.map((j) => `<tr>
          <td><a href="/analyses/${j.id}/">${j.id}</a></td>
          <td class="nowrap">${Util.esc(j.input_type_display)}</td>
          <td>${j.expected_action ? Util.esc(j.expected_action_display) : "-"}</td>
          <td>${j.predictions.map(View.predictionLine).join("<br>") || (j.status === "FAILURE" ? `<span class="error">${Util.esc(j.error_message)}</span>` : Util.esc(j.result_message) || "-")}</td>
          <td>${View.badge(j.status)}</td>
          <td class="nowrap">${Util.sec(j.processing_seconds)}</td>
          <td class="nowrap">${Util.time(j.created_at)}</td></tr>`).join("")
        : '<tr><td colspan="7" class="muted">아직 분석 기록이 없습니다.</td></tr>';
    },
    detail(job) {
      Util.$("#detail-status").outerHTML = `<span id="detail-status">${View.badge(job.status)}</span>`;
      const meta = [
        ["입력 방식", job.input_type_display + (job.camera_name ? ` (${Util.esc(job.camera_name)})` : "")],
        ["영상", Util.esc(job.video_name) || "-"],
        ["수행한 동작(사용자 선택)", job.expected_action ? Util.esc(job.expected_action_display) : "-"],
        ["영상 길이 / AI 처리 시간", `${Util.sec(job.video_seconds)} / ${Util.sec(job.processing_seconds)}`],
        ["요청 / 완료", `${Util.time(job.created_at)} / ${Util.time(job.finished_at)}`],
        ["Celery Task ID", `<code>${Util.esc(job.celery_task_id)}</code>`],
      ];
      Util.$("#detail-meta").innerHTML = meta.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
      Util.$("#detail-result").innerHTML = View.resultTable(job) || `<p class="muted">${Config.statusKo[job.status]}…</p>`;
    },
  };

  // ── Handlers ──
  const state = { input: "UPLOAD", polling: null };

  async function poll(id, onDone, count = 0) {
    try {
      const s = await Data.status(id);
      if (s.is_finished) return onDone(await Data.detail(id));
      if (Util.$("#current")) View.current({ id, status: s.status });
      if (count < Config.pollLimit) state.polling = setTimeout(() => poll(id, onDone, count + 1), Config.pollMs);
    } catch (err) {
      state.polling = setTimeout(() => poll(id, onDone, count + 1), Config.pollMs * 2);
    }
  }

  const Handlers = {
    switchTab(e) {
      state.input = e.currentTarget.dataset.input;
      Util.$$(".tab").forEach((t) => t.classList.toggle("active", t === e.currentTarget));
      Util.$$(".pane").forEach((p) => p.classList.toggle("hidden", p.dataset.pane !== state.input));
    },
    async submit(e) {
      e.preventDefault();
      const form = e.currentTarget;
      const err = Util.$("#form-error");
      const btn = Util.$("#start-btn");
      err.hidden = true;
      const fd = new FormData();
      fd.append("input_type", state.input);
      if (state.input === "UPLOAD") {
        const file = form.video.files[0];
        if (!file) { err.textContent = "영상 파일을 선택하세요."; err.hidden = false; return; }
        fd.append("video", file);
      } else if (form.camera_name) {
        fd.append("camera_name", form.camera_name.value);
      }
      ["expected_action", "title"].forEach((k) => fd.append(k, form[k].value));
      btn.disabled = true;
      btn.textContent = "요청 중…";
      try {
        const created = await Data.create(fd);   // 202: 분석은 아직, 작업 ID 만 받음
        View.current({ id: created.id, status: created.status });
        clearTimeout(state.polling);
        poll(created.id, (job) => { View.current(job); Handlers.refreshHistory(); });
        Handlers.refreshHistory();
        form.reset();
      } catch (ex) {
        err.textContent = Util.errorText(ex);
        err.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = "AI 분석 시작";
      }
    },
    async refreshHistory() {
      try { View.history(await Data.list()); } catch (ex) { /* 다음 새로고침 때 다시 */ }
    },
    async saveEdit(e) {
      e.preventDefault();
      const id = Util.$("#detail").dataset.jobId;
      const f = e.currentTarget;
      try {
        await Data.update(id, { title: f.title.value, memo: f.memo.value });
        Util.$("#edit-message").textContent = "저장했습니다.";
      } catch (ex) {
        Util.$("#edit-message").textContent = Util.errorText(ex);
      }
    },
    async remove() {
      const id = Util.$("#detail").dataset.jobId;
      if (!confirm(`분석 #${id} 기록과 사람별 결과, 영상 파일을 삭제할까요? 되돌릴 수 없습니다.`)) return;
      await Data.remove(id);
      location.href = "/";
    },
  };

  // ── Init ──
  const Init = {
    index() {
      Util.$$(".tab").forEach((t) => t.addEventListener("click", Handlers.switchTab));
      Util.$("#analysis-form").addEventListener("submit", Handlers.submit);
      Handlers.refreshHistory();
      // 새로고침 전에 진행 중이던 작업이 있으면 이어서 조회
      Data.list().then((jobs) => {
        const running = jobs.find((j) => !j.is_finished);
        if (running) {
          View.current(running);
          poll(running.id, (job) => { View.current(job); Handlers.refreshHistory(); });
        }
      }).catch(() => {});
    },
    detail() {
      const id = Util.$("#detail").dataset.jobId;
      Data.detail(id).then((job) => {
        View.detail(job);
        if (!job.is_finished) poll(id, View.detail);
      });
      Util.$("#edit-form").addEventListener("submit", Handlers.saveEdit);
      Util.$("#delete-btn").addEventListener("click", Handlers.remove);
    },
  };

  // ── Entry ──
  document.addEventListener("DOMContentLoaded", () => {
    if (Util.$("#analysis-form")) Init.index();
    if (Util.$("#detail")) Init.detail();
  });
})();
