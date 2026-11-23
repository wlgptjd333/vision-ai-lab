/* 관리자 대시보드: Django 가 ORM 으로 집계해 json_script 로 넘긴 값으로 Chart.js 차트를 그린다.
 * (FastAPI 는 DB 를 모른다 — 집계는 Django 몫)
 * 구성: Config · Data · View · Entry
 */
(function () {
  "use strict";

  // ── Config ──
  const css = getComputedStyle(document.documentElement);
  const color = (name) => css.getPropertyValue(name).trim();
  const Config = {
    predictedColor: "#2563eb",
    uncertainColor: "#93c5fd",
    statusColor: { SUCCESS: "#15803d", FAILURE: "#b91c1c", STARTED: "#d97706", PENDING: "#64748b" },
  };

  // ── Data ──
  const Data = { chart: JSON.parse(document.getElementById("chart-data").textContent) };

  // ── View ──
  const View = {
    base() {
      Chart.defaults.color = color("--muted") || "#555";
      Chart.defaults.borderColor = color("--line") || "#ddd";
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    },
    actionChart() {
      const rows = Data.chart.actions;
      new Chart(document.getElementById("actionChart"), {
        type: "bar",
        data: {
          labels: rows.map((r) => `${r.id} ${r.name_ko}`),
          datasets: [
            { label: "예측 건수 (확실)", data: rows.map((r) => r.count - r.uncertain),
              backgroundColor: Config.predictedColor },
            { label: "판단 불확실", data: rows.map((r) => r.uncertain),
              backgroundColor: Config.uncertainColor },
          ],
        },
        options: {
          indexAxis: "y", maintainAspectRatio: false,
          scales: { x: { stacked: true, beginAtZero: true, ticks: { precision: 0 } }, y: { stacked: true } },
          plugins: { legend: { position: "bottom" } },
        },
      });
    },
    statusChart() {
      const rows = Data.chart.statuses;
      new Chart(document.getElementById("statusChart"), {
        type: "doughnut",
        data: {
          labels: rows.map((r) => `${r.label} (${r.status})`),
          datasets: [{ data: rows.map((r) => r.count), backgroundColor: rows.map((r) => Config.statusColor[r.status]) }],
        },
        options: { maintainAspectRatio: false, plugins: { legend: { position: "right" } } },
      });
    },
    inputChart() {
      const rows = Data.chart.inputs;
      new Chart(document.getElementById("inputChart"), {
        data: {
          labels: rows.map((r) => r.label),
          datasets: [
            { type: "bar", label: "작업 수", data: rows.map((r) => r.count), backgroundColor: "#2563eb", yAxisID: "y" },
            { type: "bar", label: "평균 AI 처리 시간(초)", data: rows.map((r) => r.avg_seconds), backgroundColor: "#94a3b8", yAxisID: "y1" },
          ],
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "작업 수" } },
            y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "초" } },
          },
          plugins: { legend: { position: "bottom" } },
        },
      });
    },
  };

  // ── Entry ──
  document.addEventListener("DOMContentLoaded", () => {
    View.base();
    View.actionChart();
    View.statusChart();
    View.inputChart();
  });
})();
