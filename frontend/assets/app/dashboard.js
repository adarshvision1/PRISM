"use strict";
document.body.classList.add("single-page");
const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const COLORS = ["#a9ad86", "#b6a08a", "#cfa675", "#83b0be"],
  NAMES = [
    "drivable",
    "non-drivable-terrain",
    "static-obstacle",
    "Dynamic-object semantic segmentation",
  ];
import("/assets/features/presentation.js?v=20260928-spa15").then(({ curateJudgeView }) =>
  curateJudgeView(),
);
const fmt = (v, n = 1) =>
  v !== null && v !== undefined && Number.isFinite(Number(v))
    ? Number(v).toLocaleString(undefined, {
        maximumFractionDigits: n,
        minimumFractionDigits: n,
      })
    : "—";
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const api = import("/assets/app/api.js");
const get = (...args) => api.then((module) => module.get(...args));
let evidence,
  benchViewer,
  launchViewer,
  activeJob = null,
  polling = false;
const chartConfig = new WeakMap();
const chartWidth = new WeakMap();
const chartResize = new ResizeObserver((entries) => {
  for (const { target } of entries) {
    const width = Math.round(target.clientWidth);
    if (width > 0 && Math.abs(width - (chartWidth.get(target) || 0)) > 3) {
      const config = chartConfig.get(target);
      if (config) svgChart(target, config.series, config.options);
    }
  }
});
function svgChart(el, series, options = {}) {
  const W = Math.max(320, Math.round(el.clientWidth || 560)),
    H = el.classList.contains("compact") ? 130 : 210,
    L = 56,
    R = 22,
    T = 22,
    B = 43,
    innerW = W - L - R,
    innerH = H - T - B;
  chartConfig.set(el, { series, options });
  chartWidth.set(el, Math.round(el.clientWidth || W));
  if (!el.dataset.chartResizeObserved) {
    chartResize.observe(el);
    el.dataset.chartResizeObserved = "true";
  }
  const all = series.flatMap((s) =>
    s.points.filter((p) => p.y !== null && Number.isFinite(p.y)),
  );
  if (!all.length) {
    el.innerHTML =
      '<div class="chart-empty">No measured data available yet.</div>';
    return;
  }
  let xmin = options.xmin ?? Math.min(...all.map((p) => p.x)),
    xmax = options.xmax ?? Math.max(...all.map((p) => p.x));
  if (xmax === xmin) xmax = xmin + 1;
  let ymin = options.ymin ?? 0,
    ymax =
      options.ymax ?? Math.max(...all.map((p) => p.y + (p.spread || 0))) * 1.12;
  if (ymax <= ymin) ymax = ymin + 1;
  const X = (x) => L + ((x - xmin) / (xmax - xmin)) * innerW,
    Y = (y) => T + innerH - ((y - ymin) / (ymax - ymin)) * innerH;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(options.title || "Measured chart")}">`;
  for (let i = 0; i <= 4; i++) {
    let v = ymin + ((ymax - ymin) * i) / 4;
    s += `<path class="guide" d="M${L} ${Y(v)}H${W - R}"/><text x="${L - 8}" y="${Y(v) + 3}" text-anchor="end">${fmt(v, options.ydecimals ?? 0)}</text>`;
  }
  const ticks =
    options.xticks ||
    Array.from({ length: 5 }, (_, i) => ({
      x: xmin + ((xmax - xmin) * i) / 4,
      label: fmt(xmin + ((xmax - xmin) * i) / 4, 0),
    }));
  for (const t of ticks)
    s += `<text x="${X(t.x)}" y="${H - B + 20}" text-anchor="middle">${esc(t.label)}</text>`;
  s += `<path class="axis" d="M${L} ${T}V${H - B}H${W - R}"/><text x="${L}" y="11">${esc(options.ylabel || "")}</text><text x="${W - R}" y="${H - 4}" text-anchor="end">${esc(options.xlabel || "")}</text>`;
  for (const seriesItem of series) {
    let points = seriesItem.points,
      color = seriesItem.color;
    let segments = [],
      current = [];
    for (const p of points) {
      if (p.y === null) {
        if (current.length) segments.push(current);
        current = [];
      } else current.push(p);
    }
    if (current.length) segments.push(current);
    for (const ps of segments) {
      if (!options.scatter) {
        const path = ps
          .map((p, i) => `${i ? "L" : "M"}${X(p.x)} ${Y(p.y)}`)
          .join(" ");
        if (options.area)
          s += `<path d="${path}L${X(ps.at(-1).x)} ${Y(ymin)}L${X(ps[0].x)} ${Y(ymin)}Z" fill="${color}" opacity=".1"/>`;
        if (ps.some((p) => p.spread)) {
          const a = ps.map(
              (p) => `${X(p.x)},${Y(Math.min(ymax, p.y + (p.spread || 0)))}`,
            ),
            b = [...ps]
              .reverse()
              .map(
                (p) => `${X(p.x)},${Y(Math.max(ymin, p.y - (p.spread || 0)))}`,
              );
          s += `<polygon points="${[...a, ...b].join(" ")}" fill="${color}" opacity=".15"/>`;
        }
        s += `<path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>`;
      }
      for (const p of ps)
        s += `<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="${options.scatter ? 5 : 2.5}" fill="${color}" data-chart-name="${esc(seriesItem.name)}" data-chart-x="${esc(fmt(p.x, 0))}" data-chart-y="${esc(fmt(p.y, 2))}"><title>${esc(seriesItem.name)}: ${fmt(p.x)}, ${fmt(p.y, 2)}</title></circle>`;
    }
  }
  s += "</svg>";
  el.innerHTML = s;
  const chartTip = document.createElement("div");
  chartTip.className = "chart-tooltip";
  el.append(chartTip);
  el.querySelectorAll("circle[data-chart-name]").forEach((point) => {
    point.addEventListener("pointerenter", () => {
      const xLabel = options.xName || options.xlabel || "x";
      const yLabel = options.yName || options.ylabel || "value";
      chartTip.innerHTML = `<b>${point.dataset.chartName}</b><span>${esc(xLabel)} ${point.dataset.chartX}</span><strong>${point.dataset.chartY} ${esc(yLabel)}</strong>`;
      chartTip.classList.add("visible");
    });
    point.addEventListener("pointerleave", () =>
      chartTip.classList.remove("visible"),
    );
  });
  el.insertAdjacentHTML(
    "beforeend",
    `<div class="legend">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}</div>`,
  );
}
function renderEvidence(data) {
  evidence = data;
  const run = data.training || {},
    curve = data.curve || [];
  svgChart(
    $("#training-chart"),
    [
      {
        name: "Validation block mIoU",
        color: "#71969f",
        points: curve.map((r) => ({ x: +r.epoch, y: +r.val_miou * 100 })),
      },
    ],
    {
      ylabel: "mIoU (%)",
      xlabel: "epoch",
      xName: "Epoch",
      yName: "mIoU (%)",
      ymax: 100,
      xmin: 1,
      title: "Validation mIoU by completed epoch",
    },
  );
  $("#training-note").textContent = "";
  const rows = [
    ["Dataset", "SemanticKITTI"],
    ["Train split", "00–07, 09, 10"],
    ["Block / input", "10 × 10 m / 4,096 near · 1,024 far"],
    ["Training device", run.gpu || "Checking local device"],
    [
      "Best block mIoU",
      run.best_val_miou != null
        ? fmt(run.best_val_miou * 100, 2) + "%"
        : "Pending",
    ],
    ["Checkpoint rule", "Best validation mIoU"],
  ];
  $("#model-card").innerHTML = rows
    .map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`)
    .join("");
  renderBenchmark(data.benchmark, data.demo);
  window.dispatchEvent(new CustomEvent('prism:evidence-loaded'));
}
const modeNames = {
    uniform: "Uniform",
    distance: "Distance-only",
    ground: "Ground-aware",
    semantic: "Semantic-aware",
    prism: "PRISM",
  },
  modeColors = {
    uniform: "#7895a5",
    distance: "#88a991",
    ground: "#9d91ad",
    semantic: "#61879b",
    prism: "#e8b86d",
  };
function renderBenchmark(b, demo) {
  const snapshotTitle = $('#ablation-table')?.closest('article')?.querySelector('h3');
  if (snapshotTitle && b) snapshotTitle.textContent = `Earlier point-level evaluation · epoch ${b.model?.epoch ?? 'unknown'} · ${b.frames} scans`;
  if (!b) {
    $("#benchmark-status").innerHTML =
      "<strong>Evaluation pending</strong><span>The benchmark accepts a trained checkpoint only. Interim predictions are excluded from accuracy charts.</span>";
    ["memory-chart", "frontier-chart", "distance-chart"].forEach(
      (id) =>
        ($("#" + id).innerHTML =
          '<div class="chart-empty">Waiting for trained-checkpoint evaluation.</div>'),
    );
    $("#heatmap").textContent = "No measured heatmap yet.";
    return;
  }
  $("#benchmark-status").innerHTML =
    `<strong>${fmt(b.frames, 0)} validation scans · ${esc(b.hardware.device)}</strong><span>Checkpoint epoch ${b.model.epoch} · ${esc(b.model.sha256.slice(0, 12))}<br>${esc(b.coverage)}</span>`;
  const modes = b.modes;
  svgChart(
    $("#frontier-chart"),
    Object.entries(modes).map(([k, v]) => ({
      name: modeNames[k],
      color: modeColors[k],
      points: [{ x: v.cells / 1000, y: v.pipeline_fps }],
    })),
    {
      scatter: true,
      xmin: 0,
      ylabel: "Pipeline FPS",
      xlabel: "active cells (thousands)",
      ydecimals: 2,
      title: "Memory and processing speed tradeoff",
    },
  );
  svgChart(
    $("#distance-chart"),
    ["uniform", "prism"].map((k) => ({
      name: modeNames[k],
      color: modeColors[k],
      points: modes[k].bands.map((v, i) => ({
        x: i,
        y: v.miou === null ? null : v.miou * 100,
        spread: (v.spread || 0) * 100,
      })),
    })),
    {
      ylabel: "mIoU (%)",
      xlabel: "distance (m)",
      ymax: 100,
      xmin: 0,
      xmax: 3,
      xticks: ["0–10", "10–25", "25–60", "60–100"].map((label, x) => ({
        label,
        x,
      })),
      title: "Accuracy by distance with frame spread",
    },
  );
  $("#heatmap").innerHTML =
    '<div class="heat-row header"><span>08 / chunk</span><span>0–10 m</span><span>10–25 m</span><span>25–60 m</span><span>60–100 m</span></div>' +
    b.chunks
      .map(
        (c, i) =>
          `<div class="heat-row"><span>${String(i + 1).padStart(2, "0")} · n=${c.frames}</span>${c.delta.map((v, j) => `<span title="Frames ${c.start}–${c.end}; band ${j + 1}; delta ${v === null ? "unavailable" : fmt(v * 100, 3) + " percentage points"}" style="background:${v === null ? "#e0e7e7" : v >= 0 ? `rgba(232,184,109,${0.12 + Math.min(Math.abs(v) * 100, 0.7)})` : `rgba(120,149,165,${0.12 + Math.min(Math.abs(v) * 100, 0.7)})`}">${v === null ? "—" : (v > 0 ? "+" : "") + fmt(v * 100, 2)}</span>`).join("")}</div>`,
      )
      .join("") +
    '<div class="heat-legend">Grey-blue: uniform better · saffron: PRISM better · —: no valid labels</div>';
  const intervalsTieAtDisplayPrecision = b.chunks.every((chunk) =>
    chunk.delta.every((value) => value === null || Math.abs(value * 100) < 0.005),
  );
  if (intervalsTieAtDisplayPrecision) {
    const heatmapCard = $("#heatmap")?.closest(".panel");
    if (heatmapCard) heatmapCard.hidden = true;
    const distanceNote = $("#distance-chart")?.closest(".panel")?.querySelector(".caption");
    if (distanceNote) distanceNote.textContent = "mIoU by distance band; shaded ±1 frame standard deviation. Across all 10 contiguous sequence-08 intervals, both maps tie at displayed precision on shared 5 cm cells.";
  } else {
    const heatmapCard = $("#heatmap")?.closest(".panel");
    if (heatmapCard) heatmapCard.hidden = false;
  }
  const ablationTable = $("#ablation-table");
  if (ablationTable) ablationTable.innerHTML =
    "<table><thead><tr><th>Policy</th><th>Pipeline FPS</th><th>Grid ms</th><th>Cells</th><th>Leaf MiB</th><th>mIoU</th><th>Drivable IoU</th><th>Terrain IoU</th><th>Static IoU</th><th>Object IoU</th></tr></thead><tbody>" +
    Object.entries(modes)
      .map(
        ([k, v]) =>
          `<tr class="${k === "prism" ? "prism-row" : ""}"><td>${modeNames[k]}</td><td>${fmt(v.pipeline_fps, 2)}</td><td>${fmt(v.grid_ms, 1)}</td><td>${fmt(v.cells, 0)}</td><td>${fmt(v.bytes / 1048576, 2)}</td><td>${fmt(v.miou * 100, 2)}%</td>${v.iou.map((x) => `<td>${x === null ? "—" : fmt(x * 100, 2) + "%"}</td>`).join("")}</tr>`,
      )
      .join("") +
    "</tbody></table>";
  const coverageNote = $("#coverage-note");
  if (coverageNote) coverageNote.textContent =
    `${b.coverage} Shared model inference: ${fmt(b.inference_ms, 1)} ms/scan. Process peak RSS: ${fmt(b.peak_rss_mb, 1)} MiB; peak GPU allocation: ${fmt(b.peak_gpu_mb, 1)} MiB. Leaf storage excludes network, point arrays, and temporary workspaces.`;
  const voxelNote = $("#voxel-note");
  if (voxelNote) {
    voxelNote.textContent = b.voxel_note || "";
    if (!voxelNote.textContent.trim()) voxelNote.closest(".panel")?.remove();
  }
  if (demo) {
    $("#chunk-selector").innerHTML = demo.chunks
      .map(
        (c, i) =>
          `<button data-chunk="${i}" class="${i === 0 ? "active" : ""}">08 / ${String(i + 1).padStart(2, "0")}</button>`,
      )
      .join("");
    $("#chunk-selector")
      .querySelectorAll("button")
      .forEach(
        (button) => (button.onclick = () => loadChunk(+button.dataset.chunk)),
      );
    loadChunk(0);
  }
}

class Viewer {
  constructor(container, single = false) {
    Object.assign(this, {
      container,
      single,
      frames: [],
      index: 0,
      playing: false,
      fps: 10,
      yaw: 0,
      zoom: 1,
      view: "god",
      mode: single ? "console" : "fusion",
      threshold: 0.5,
      grid: true,
      boxes: true,
      speed: 0,
      request: 0,
      hits: [],
      selectedBox: null,
      foveaHeading: 0,
    });
    container.innerHTML = `<div class="viewport-toolbar"><span class="view-title">${single ? "ELEVATION MAP" : "LIVE FUSION"}</span><div><button class="camera-reset" title="Reset camera, zoom and fovea direction" aria-label="Reset camera, zoom and fovea direction">↻ Reset</button><button class="view-toggle" title="Toggle God View or Driver POV" aria-label="Toggle God View or Driver POV">God / Driver</button><button class="grid-toggle active">Grid</button><button class="boxes-toggle active">Boxes</button></div></div><div class="tvs"><div class="tv uniform"><div class="tv-label"><b>BASELINE</b><span>MEASURED GRID</span></div><div class="screen"><canvas aria-label="Baseline point cloud; drag to rotate, wheel to zoom"></canvas><div class="screen-rec">● CACHED FRAME <span class="frame-code">0000</span></div><div class="screen-scale">x forward · y left · z up / metres</div></div><div class="tv-stats"></div></div><div class="tv prism"><div class="tv-label"><b>PRISM / ADAPTIVE ELEVATION</b><span>5 → 10 → 25 → 50 CM</span></div><div class="screen"><canvas aria-label="PRISM point cloud; drag to rotate, wheel to zoom"></canvas><div class="screen-rec">● CACHED FRAME <span class="frame-code">0000</span></div><div class="screen-scale">x forward · y left · z up / metres</div><div class="cell-tooltip" hidden></div>${single ? '<div class="raw-inset"><span>RAW INPUT / SAME FRAME</span><canvas aria-label="Raw point-cloud inset"></canvas></div>' : ""}<div class="map-key">HEIGHT <i></i> LOW → HIGH</div></div><div class="tv-stats"></div></div></div><div class="fusion-controls"><label class="control-card"><span>DRIVING ATTENTION</span><output>0 km/h</output><input class="fovea-speed" aria-label="Fovea speed in kilometres per hour" type="range" min="0" max="60" value="0"><div class="range-hints"><span>0</span><span>30</span><span>60 km/h</span></div></label><div class="control-status"><b class="fusion-state">Recorded frame grid</b><small>Speed reshapes the focus region. Segmentation stays cached.</small></div></div><div class="timeline"><button class="play">▶ Play</button><button class="step" aria-label="Step one frame">⏭</button><button class="reset" aria-label="Reset replay">↺</button><input class="scrub" aria-label="Frame timeline" type="range" min="0" max="0" value="0"><span class="counter">0 / 0</span><select class="speed" aria-label="Replay speed"><option value="5">0.5×</option><option value="10" selected>1×</option><option value="20">2×</option><option value="40">4×</option></select></div><div class="viewer-caption"><span class="frame-detail">Select a scene to begin.</span><span>Cached replay · 10 Hz</span></div>`;
    this.canvases = [
      container.querySelector(".uniform canvas"),
      container.querySelector(".prism .screen>canvas"),
    ];
    this.scrub = container.querySelector(".scrub");
    this.playButton = container.querySelector(".play");
    this.playButton.onclick = () => this.setPlaying(!this.playing);
    container.querySelector(".step").onclick = () => {
      this.setPlaying(false);
      this.show((this.index + 1) % Math.max(1, this.frames.length));
    };
    container.querySelector(".reset").onclick = () => {
      this.setPlaying(false);
      this.show(0);
    };
    this.scrub.oninput = () => {
      this.setPlaying(false);
      this.show(+this.scrub.value);
    };
    container.querySelector(".speed").onchange = (e) =>
      (this.fps = +e.target.value);
    container.querySelector(".view-toggle").onclick = () => {
      this.view = this.view === "god" ? "driver" : "god";
      this.draw();
    };
    container.querySelector(".camera-reset").onclick = () => {
      this.yaw = 0;
      this.zoom = 1;
      this.view = "god";
      this.foveaHeading = 0;
      const heading = container.querySelector(".heading-input");
      if (heading) heading.value = "0";
      const turn = container.querySelector(".turn-label");
      if (turn) turn.textContent = "STRAIGHT";
      container.querySelector(".view-toggle").textContent =
        "God View ↔ Driver POV";
      this.draw();
      this.regrid();
    };
    ["grid", "boxes"].forEach(
      (k) =>
        (container.querySelector("." + k + "-toggle").onclick = (e) => {
          this[k] = !this[k];
          e.target.classList.toggle("active", this[k]);
          this.draw();
        }),
    );
    container.querySelector(".fovea-speed").oninput = (e) => {
      this.speed = +e.target.value;
      container.querySelector(".fusion-controls output").textContent =
        this.speed + " km/h";
      this.setPlaying(false);
      clearTimeout(this.debounce);
      container.querySelector(".fusion-state").textContent =
        "Rebuild requested…";
      this.debounce = setTimeout(() => this.regrid(), 120);
    };
    for (const c of this.canvases) {
      c.onpointerdown = (e) => {
        this.drag = e.clientX;
        c.setPointerCapture(e.pointerId);
      };
      c.onpointerup = () => {
        this.drag = null;
        if (this.frame) {
          this.setPlaying(false);
          this.regrid();
        }
      };
      c.onpointermove = (e) => {
        if (e.buttons && this.drag != null) {
          this.yaw += (e.clientX - this.drag) * 0.008;
          this.foveaHeading = Math.atan2(
            Math.sin(this.yaw),
            Math.cos(this.yaw),
          );
          const heading = this.container.querySelector(".heading-input");
          if (heading)
            heading.value = String((-this.foveaHeading * 180) / Math.PI);
          this.drag = e.clientX;
          this.draw();
        } else this.hover(c, e);
      };
      c.onpointerleave = () =>
        (container.querySelector(".cell-tooltip").hidden = true);
      c.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          this.zoom = Math.max(
            0.45,
            Math.min(8, this.zoom * Math.exp(-e.deltaY * 0.001)),
          );
          this.draw();
        },
        { passive: false },
      );
    }
    new ResizeObserver(() => this.draw()).observe(container);
    this.setMode(this.mode);
    let tick = 0;
    const loop = (t) => {
      if (
        this.playing &&
        this.frames.length > 1 &&
        t - tick > 1000 / this.fps
      ) {
        this.show((this.index + 1) % this.frames.length);
        tick = t;
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  setPlaying(v) {
    this.playing = v;
    this.playButton.textContent = v ? "Ⅱ Pause" : "▶ Play";
  }
  setMode(mode) {
    this.mode = mode;
    this.container.dataset.mode = mode;
    this.container.querySelector(".view-title").textContent = {
      representation: "PERCEPTION LAB / REPRESENTATION",
      resolution: "PERCEPTION LAB / RESOLUTION",
      fusion: "PERCEPTION LAB / LIVE FUSION",
      quad: "PERCEPTION LAB / SYNCHRONIZED",
      console: "ELEVATION MAP / SEMANTIC PREDICTIONS",
    }[mode];
    this.container.querySelector(".uniform .tv-label b").textContent =
      mode === "representation"
        ? "DENSE 3D / 5 CM VOXELS"
        : "UNIFORM HIGH-RES / 5 CM";
    this.container.querySelector(".prism .tv-label b").textContent =
      mode === "representation"
        ? "SPARSE 2.5D / VARIABLE CELLS"
        : "PRISM / ADAPTIVE ELEVATION";
    if (mode === "representation" && this.frame && !this.fusion) this.regrid();
    this.updateStats();
    this.draw();
  }
  setFrames(frames) {
    this.request++;
    this.frames = frames;
    this.fusion = null;
    this.setPlaying(false);
    this.scrub.max = Math.max(0, frames.length - 1);
    this.show(0);
  }
  append(frame) {
    this.frames.push(frame);
    this.scrub.max = this.frames.length - 1;
    if (this.frames.length === 1 || this.index === this.frames.length - 2)
      this.show(this.frames.length - 1);
  }
  show(index) {
    this.index = Math.max(0, Math.min(index, this.frames.length - 1));
    this.frame = this.frames[this.index];
    this.fusion = null;
    this.request++;
    this.scrub.value = this.index;
    this.container.querySelector(".counter").textContent =
      `${this.frames.length ? this.index + 1 : 0} / ${this.frames.length}`;
    this.container
      .querySelectorAll(".frame-code")
      .forEach(
        (el) => (el.textContent = String(this.index + 1).padStart(4, "0")),
      );
    if (this.frame) {
      const f = this.frame;
      this.container.querySelector(".frame-detail").textContent =
        `${f.name} · ${fmt(f.point_count, 0)} points · ${fmt(f.timing.processing_ms, 0)} ms recorded processing`;
      this.container.querySelector(".fusion-state").textContent =
        "Original recorded grid";
      this.speed = f.speed_mps * 3.6 || 0;
      this.foveaHeading = f.heading || 0;
      const headingInput = this.container.querySelector(".heading-input");
      if (headingInput)
        headingInput.value = (this.foveaHeading * 180) / Math.PI;
      this.container.querySelector(".fovea-speed").value = Math.min(
        60,
        this.speed,
      );
      this.container.querySelector(".fusion-controls output").textContent =
        fmt(this.speed, 0) + " km/h";
      if (this.onFrame) this.onFrame(f, this.index);
    }
    this.updateStats();
    this.draw();
    if (this.mode === "representation" && this.frame && !this.playing)
      this.regrid();
  }
  async regrid() {
    if (!this.frame) return;
    const token = ++this.request;
    const responseStart = performance.now();
    const status = this.container.querySelector(".fusion-state");
    status.textContent = "Computing full-cloud grid…";
    const body = {
      demo_index: this.frame.demo_index ?? 0,
      speed_kmh: Math.min(60, this.speed),
      heading: this.foveaHeading,
    };
    if (this.single) {
      body.job_id = activeJob;
      body.frame_index = this.index;
    }
    try {
      const r = await fetch("/api/fusion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
        data = await r.json();
      if (!r.ok) throw Error(data.detail);
      if (token !== this.request) return;
      this.fusion = data;
      data.response_ms = performance.now() - responseStart;
      status.textContent = `${fmt(data.prism.grid_ms, 1)} ms adaptive grid · ${fmt(data.input_points, 0)} source points · ${fmt(data.response_ms, 0)} ms turn response`;
      this.updateStats();
      this.draw();
    } catch (e) {
      if (token === this.request) status.textContent = e.message;
    }
  }
  updateStats() {
    if (!this.frame) return;
    const f = this.frame;
    ["uniform", "prism"].forEach((m) => {
      let g = this.fusion?.[m] || f.grids[m],
        scope = "GRID ONLY";
      if (this.mode === "representation") {
        g = m === "uniform" ? this.fusion?.voxel : this.fusion?.local;
        scope = "LOCAL CROP / GRID ONLY";
      }
      const ms = g?.grid_ms;
      this.container.querySelector("." + m + " .tv-stats").innerHTML =
        [
          ["STORAGE", g ? fmt(g.bytes / 1048576, 2) : "—", "MiB"],
          ["GRID RATE", ms ? fmt(1000 / ms, 1) : "—", "Hz"],
          ["DISPLAY", g ? fmt(g.cells.length, 0) : "—", "cells"],
          ["LATENCY", ms ? fmt(ms, 1) : "—", "ms"],
        ]
          .map(
            ([a, b, c]) => `<span><small>${a}</small><b>${b}</b> ${c}</span>`,
          )
          .join("") +
        `<small class="scope-label">${scope} · ${this.mode === "representation" ? "20 × 20 × 4 m" : "network + detection excluded"}</small>`;
    });
  }
  hover(canvas, e) {
    if (canvas !== this.canvases[1]) return;
    const rect = canvas.getBoundingClientRect(),
      x = ((e.clientX - rect.left) * canvas.width) / rect.width,
      y = ((e.clientY - rect.top) * canvas.height) / rect.height;
    let best = null,
      dist = 160;
    for (const h of this.hits) {
      const d = (h[0] - x) ** 2 + (h[1] - y) ** 2;
      if (d < dist) {
        dist = d;
        best = h[2];
      }
    }
    const tip = this.container.querySelector(".cell-tooltip");
    tip.hidden = !best;
    if (best) {
      tip.style.left =
        Math.min(rect.width - 210, e.clientX - rect.left + 12) + "px";
      tip.style.top = Math.max(32, e.clientY - rect.top - 70) + "px";
      tip.innerHTML = `<b>${esc(NAMES[best[3]] || "unknown")}</b><br>Resolution ${fmt(best[2] * 100, 0)} cm · ${fmt(Math.hypot(best[0], best[1]), 1)} m<br>Confidence ${fmt(best[5] * 100, 1)}% · height ${fmt(best[4], 2)} m`;
    }
  }
  draw() {
    const start = performance.now();
    this.canvases.forEach((c, i) => this.drawScene(c, i ? "prism" : "uniform"));
    if (this.single) {
      const c = this.container.querySelector(".raw-inset canvas");
      this.drawScene(c, "raw");
    }
    this.renderMs = performance.now() - start;
  }
  drawScene(canvas, mode) {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = Math.min(devicePixelRatio || 1, 1.5),
      w = Math.round(rect.width * dpr),
      h = Math.round(rect.height * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#253a46";
    ctx.fillRect(0, 0, w, h);
    const god = this.view === "god",
      repr = this.mode === "representation" || mode === "voxel",
      scale =
        (Math.min(w, h) / (this.mode === "quad" ? 24 : repr ? 24 : 80)) *
        this.zoom,
      co = Math.cos(this.yaw),
      si = Math.sin(this.yaw);
    const project = (x, y, z) => {
      const xx = x * co - y * si,
        yy = x * si + y * co;
      if (god)
        return [
          w * 0.5 - yy * scale,
          h * (this.mode === "quad" ? 0.7 : repr ? 0.5 : 0.7) - xx * scale,
          Math.hypot(x, y),
        ];
      const X = xx + 12,
        Z = z - 8,
        depth = X * 0.973 - Z * 0.23;
      if (depth < 1) return null;
      return [
        w * 0.5 - (yy * w * 0.95 * this.zoom) / depth,
        h * 0.43 - ((X * 0.23 + Z * 0.973) * w * 0.95 * this.zoom) / depth,
        depth,
      ];
    };
    const line = (a, b) => {
      const p = project(...a),
        q = project(...b);
      if (p && q) {
        ctx.moveTo(p[0], p[1]);
        ctx.lineTo(q[0], q[1]);
      }
    };
    ctx.lineWidth = 0.6 * dpr;
    ctx.strokeStyle = "#a3b9c431";
    ctx.beginPath();
    for (let x = -100; x <= 100; x += 10) line([x, -100, -1.7], [x, 100, -1.7]);
    for (let y = -100; y <= 100; y += 10) line([-100, y, -1.7], [100, y, -1.7]);
    ctx.stroke();
    if (!this.frame) {
      ctx.fillStyle = "#a1b5bf";
      ctx.font = `${12 * dpr}px monospace`;
      ctx.textAlign = "center";
      ctx.fillText(
        this.single
          ? "Run a sequence to populate the map"
          : "Loading local scene…",
        w / 2,
        h / 2,
      );
      return;
    }
    const f = this.frame;
    if (mode === "prism") this.hits = [];
    const inCrop = (p) =>
      !repr ||
      (p[0] >= -10 &&
        p[0] < 10 &&
        p[1] >= -10 &&
        p[1] < 10 &&
        p[2] >= -3 &&
        p[2] < 1);
    const drawPointCloud =
      mode === "raw" ||
      mode === "semantic" ||
      (!(repr && mode !== "raw") &&
        (!this.diagnostic || this.diagnostic === "semantic"));
    if (drawPointCloud)
      for (const p of f.points) {
        if (!inCrop(p)) continue;
        const q = project(...p);
        if (!q || q[0] < 0 || q[0] > w || q[1] < 0 || q[1] > h) continue;
        ctx.fillStyle = mode === "raw" ? "#adbec4" : COLORS[p[3]] || "#647585";
        ctx.globalAlpha = Math.max(0.55, 1 - q[2] / 200);
        const sz = (mode === "raw" ? 1 : Math.max(0.8, 2 - q[2] / 85)) * dpr;
        ctx.fillRect(q[0], q[1], sz, sz);
      }
    ctx.globalAlpha = 1;
    if (mode === "raw" || mode === "semantic") return;
    if (
      (repr && mode === "uniform" && (this.fusion || f.voxel)) ||
      mode === "voxel"
    ) {
      ctx.strokeStyle = "#cbbba5bb";
      ctx.lineWidth = 0.7 * dpr;
      ctx.beginPath();
      for (const c of (this.fusion?.voxel || f.voxel || { cells: [] }).cells) {
        const [x, y, z] = c,
          s = 0.05;
        const vertices = [
          [x, y, z],
          [x + s, y, z],
          [x + s, y + s, z],
          [x, y + s, z],
          [x, y, z + s],
          [x + s, y, z + s],
          [x + s, y + s, z + s],
          [x, y + s, z + s],
        ];
        const projected = vertices.map((p) => project(...p));
        for (const [a, b] of [
          [0, 1],
          [1, 2],
          [2, 3],
          [3, 0],
          [4, 5],
          [5, 6],
          [6, 7],
          [7, 4],
          [0, 4],
          [1, 5],
          [2, 6],
          [3, 7],
        ]) {
          const p = projected[a],
            q = projected[b];
          if (p && q) {
            ctx.moveTo(p[0], p[1]);
            ctx.lineTo(q[0], q[1]);
          }
        }
      }
      ctx.stroke();
    } else if (this.grid) {
      const g = repr
        ? this.fusion?.local
        : this.fusion?.[mode] || f.grids[mode];
      if (g) {
        ctx.lineWidth = 0.7 * dpr;
        for (const c of g.cells) {
          const [x, y, s, cls, z] = c;
          if (!inCrop([x, y, z])) continue;
          const q = project(x + s / 2, y + s / 2, z);
          if (!q || q[0] < 0 || q[0] > w || q[1] < 0 || q[1] > h) continue;
          if (mode === "prism") this.hits.push([q[0], q[1], c]);
          let attention = 1;
          if (this.mode === "fusion" && mode === "prism" && this.fusion) {
            const speed = (this.fusion.speed_kmh ?? this.speed) / 3.6,
              offset = Math.min(0.2 * speed, 5),
              focusX = offset * Math.cos(this.foveaHeading),
              focusY = offset * Math.sin(this.foveaHeading),
              distance = Math.hypot(x + s / 2 - focusX, y + s / 2 - focusY);
            attention = 0.28 + 0.72 * Math.exp(-distance / (18 + speed * 2));
          }
          ctx.globalAlpha = attention;
          const corners = [
            [x, y, z],
            [x + s, y, z],
            [x + s, y + s, z],
            [x, y + s, z],
          ].map((p) => project(...p));
          if (!corners.every(Boolean)) continue;
          ctx.beginPath();
          corners.forEach((p, i) =>
            i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]),
          );
          ctx.closePath();
          ctx.strokeStyle =
            mode === "uniform"
              ? "#9eafb875"
              : (COLORS[cls] || "#a6b8bd") + "8a";
          if (repr) {
            const light = Math.max(20, Math.min(85, 30 + (z + 2) * 28));
            ctx.fillStyle = `hsl(150 18% ${Math.max(55, light)}%)`;
            ctx.fill();
          } else if (s >= 0.1) {
            ctx.fillStyle =
              (COLORS[cls] || "#a6b8bd") + (s >= 0.25 ? "45" : "25");
            ctx.fill();
          }
          if (this.diagnostic && this.diagnostic !== "semantic") {
            const value =
              this.diagnostic === "confidence"
                ? 1 - c[5]
                : this.diagnostic === "dynamic"
                  ? cls === 3
                    ? 1 - c[5]
                    : null
                  : this.diagnostic === "variance"
                    ? Math.min(1, (c[8] ?? 0) / 0.1)
                    : this.diagnostic === "height"
                      ? Math.min(1, Math.abs((c[7] ?? z) - (c[6] ?? z)) / 0.5)
                      : this.diagnostic === "error"
                        ? c[9] != null && c[9] < 4
                          ? cls === c[9]
                            ? 0
                            : 1
                          : null
                        : null;
            ctx.strokeStyle =
              value == null ? "#83949e" : `hsl(${145 - value * 145} 68% 66%)`;
            ctx.fillStyle = ctx.strokeStyle;
            ctx.globalAlpha = 0.72;
            ctx.fill();
          }
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }
    }
    if (mode === "prism" && !repr) {
      const v = (this.fusion?.speed_kmh ?? this.speed) / 3.6,
        offset = Math.min(0.2 * v, 5),
        turn = this.fusion?.heading ?? f.heading ?? 0,
        focusX = offset * Math.cos(turn),
        focusY = offset * Math.sin(turn),
        elong = Math.min(1 + 0.033 * v, 2);
      for (const radius of [10, 25, 60]) {
        ctx.beginPath();
        for (let i = 0; i <= 100; i++) {
          const a = (i * Math.PI * 2) / 100,
            p = project(
              focusX +
                Math.cos(a) * radius * elong * Math.cos(turn) -
                Math.sin(a) * radius * Math.sin(turn),
              focusY +
                Math.cos(a) * radius * elong * Math.sin(turn) +
                Math.sin(a) * radius * Math.cos(turn),
              -1.7,
            );
          if (p) i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]);
        }
        ctx.strokeStyle = radius === 10 ? "#9db88bba" : "#a9bba37a";
        ctx.lineWidth = radius === 10 ? 1.5 * dpr : 0.8 * dpr;
        ctx.setLineDash(radius === 10 ? [] : [3 * dpr, 5 * dpr]);
        if (radius === 10) {
          ctx.fillStyle = "#b9d5a51a";
          ctx.fill();
          ctx.shadowColor = "#c1d5b2";
          ctx.shadowBlur = 10;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.setLineDash([]);
        const label = project(
          focusX + radius * elong * Math.cos(turn),
          focusY + radius * elong * Math.sin(turn),
          -1.7,
        );
        if (label) {
          ctx.fillStyle = "#d7edbd";
          ctx.font = `${11 * dpr}px monospace`;
          ctx.fillText(
            radius === 10
              ? "FULL DETAIL / 5 CM"
              : radius === 25
                ? "10 → 25 CM"
                : "COARSE / 50 CM",
            label[0] + 10,
            label[1],
          );
        }
      }
      const sensor = project(0, 0, -1.7),
        arrow = project(8 * Math.cos(turn), 8 * Math.sin(turn), -1.7);
      if (sensor && arrow) {
        ctx.strokeStyle = "#d7f0b6";
        ctx.fillStyle = "#e5f5d1";
        ctx.lineWidth = 2 * dpr;
        ctx.beginPath();
        ctx.moveTo(sensor[0], sensor[1]);
        ctx.lineTo(arrow[0], arrow[1]);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(sensor[0], sensor[1], 4 * dpr, 0, Math.PI * 2);
        ctx.fill();
        const angle = Math.atan2(arrow[1] - sensor[1], arrow[0] - sensor[0]);
        ctx.beginPath();
        ctx.moveTo(arrow[0], arrow[1]);
        ctx.lineTo(
          arrow[0] - 10 * dpr * Math.cos(angle - 0.5),
          arrow[1] - 10 * dpr * Math.sin(angle - 0.5),
        );
        ctx.lineTo(
          arrow[0] - 10 * dpr * Math.cos(angle + 0.5),
          arrow[1] - 10 * dpr * Math.sin(angle + 0.5),
        );
        ctx.closePath();
        ctx.fill();
      }
      const focus = project(focusX, focusY, -1.7);
      if (focus) {
        ctx.fillStyle = "#c2e0ad";
        ctx.font = `${11 * dpr}px monospace`;
        ctx.fillText(
          turn === 0
            ? "DIRECTIONAL FOVEA / STRAIGHT"
            : `TURN ${turn < 0 ? "RIGHT" : "LEFT"}: ${fmt((Math.abs(turn) * 180) / Math.PI, 0)}°`,
          focus[0] + 10,
          focus[1] - 10,
        );
      }
    }
    if (this.boxes && mode !== "voxel") {
      let count = 0;
      for (const box of f.boxes || []) {
        if (box.confidence < this.threshold || !inCrop(box.center)) continue;
        const [x, y, z] = box.center,
          q = project(x, y, z);
        if (!q || q[0] < 0 || q[0] > w || q[1] < 0 || q[1] > h) continue;
        const [sx, sy, sz] = box.size,
          bc = Math.cos(box.yaw),
          bs = Math.sin(box.yaw);
        const corners = [];
        for (const dz of [-1, 1])
          for (const [a, b] of [
            [-1, -1],
            [1, -1],
            [1, 1],
            [-1, 1],
          ])
            corners.push([
              x + ((a * sx) / 2) * bc - ((b * sy) / 2) * bs,
              y + ((a * sx) / 2) * bs + ((b * sy) / 2) * bc,
              z + (dz * sz) / 2,
            ]);
        ctx.strokeStyle = box === this.selectedBox ? "#fff" : COLORS[box.class];
        ctx.globalAlpha = box.fallback ? 0.25 : 0.9;
        ctx.lineWidth = box.fallback ? 0.7 * dpr : 1.2 * dpr;
        ctx.beginPath();
        for (let j = 0; j < 4; j++) {
          line(corners[j], corners[(j + 1) % 4]);
          line(corners[j + 4], corners[((j + 1) % 4) + 4]);
          line(corners[j], corners[j + 4]);
        }
        if (box.trail) line(box.trail[0], box.trail[1]);
        ctx.stroke();
        if (!box.fallback && count++ < 10) {
          ctx.fillStyle = COLORS[box.class];
          ctx.font = `${11 * dpr}px monospace`;
          ctx.fillText(
            `${box.class === 3 ? "object" : "static"} · ${fmt(box.confidence * 100, 0)}%`,
            q[0] + 5,
            q[1] - 5,
          );
        }
      }
      ctx.globalAlpha = 1;
    }
    ctx.strokeStyle = "#ca9a9a";
    ctx.lineWidth = 2 * dpr;
    ctx.beginPath();
    for (const ribbon of f.ribbons || [])
      for (let i = 1; i < ribbon.length; i++)
        if (inCrop(ribbon[i])) line(ribbon[i - 1], ribbon[i]);
    ctx.stroke();
    if (repr && mode === "prism" && f.ribbons?.length) {
      const p = f.ribbons[0][0],
        q = project(...p);
      if (q && inCrop(p)) {
        ctx.fillStyle = "#8dab96";
        ctx.font = `${10 * dpr}px monospace`;
        ctx.fillText(
          "↙ Height retained · geometric curb proposal",
          q[0] + 10,
          q[1] - 15,
        );
      }
    }
    const ego = project(0, 0, -1.5);
    if (ego) {
      ctx.fillStyle = "#f9fcf6";
      ctx.strokeStyle = "#a7c095";
      ctx.lineWidth = 2 * dpr;
      ctx.beginPath();
      ctx.moveTo(ego[0], ego[1] - 10 * dpr);
      ctx.lineTo(ego[0] - 5 * dpr, ego[1] + 7 * dpr);
      ctx.lineTo(ego[0] + 5 * dpr, ego[1] + 7 * dpr);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
  }
}
let chunkLoad = 0,
  selectedPreset = 0;
async function loadChunk(i) {
  const token = ++chunkLoad,
    chunk = evidence.demo?.chunks[i];
  if (!chunk) return;
  $("#chunk-selector")
    .querySelectorAll("button")
    .forEach((b) => b.classList.toggle("active", +b.dataset.chunk === i));
  benchViewer.setFrames([]);
  try {
    for (const index of chunk.indices) {
      const frame = await get("/api/demo/" + index);
      frame.demo_index = index;
      if (token !== chunkLoad) return;
      benchViewer.append(frame);
    }
    benchViewer.show(0);
    svgChart(
      $("#memory-chart"),
      ["uniform", "prism"].map((k) => ({
        name: modeNames[k],
        color: modeColors[k],
        points: benchViewer.frames.map((f, x) => ({
          x: x + 1,
          y: f.grids[k].active_cells,
        })),
      })),
      {
        area: true,
        ylabel: "active cells",
        xlabel: "scan in clip",
        xticks: [...new Set([0, Math.floor((benchViewer.frames.length - 1) / 2), benchViewer.frames.length - 1])]
          .filter((x) => x >= 0)
          .map((x) => ({ x: x + 1, label: String(x + 1) })),
      },
    );
  } catch (e) {
    $("#memory-chart").textContent = e.message;
  }
}
function showError(message) {
  $("#job-monitor").classList.add("error");
  $("#job-monitor").textContent = message;
}
async function beginFiles(list) {
  const files = [...list].filter(
    (f) => !f.webkitRelativePath || /\.(bin|pcd|ply)$/i.test(f.name),
  );
  if (!files.length)
    return showError("Choose BIN, PLY, PCD or a ZIP of those frames.");
  if (files.some((f) => !/\.(bin|pcd|ply|zip)$/i.test(f.name)))
    return showError("Unsupported format. Use BIN, PLY, PCD or ZIP.");
  if (files.reduce((s, f) => s + f.size, 0) > 500 * 1024 ** 2)
    return showError("Combined upload exceeds 500 MB.");
  if (files.length > 300)
    return showError(
      "Choose up to 300 files, or a ZIP capped at its first 300 frames.",
    );
  const body = new FormData();
  files.forEach((f) => body.append("files", f, f.name));
  $("#input-validation").textContent =
    `${files.length} files · ${fmt(files.reduce((s, f) => s + f.size, 0) / 1048576, 1)} MiB selected`;
  $("#job-monitor").textContent = "Uploading to this laptop…";
  try {
    const architecture = document.querySelector('#architecture-select')?.value || 'pointnet2';
    const r = await fetch('/api/jobs?architecture='+encodeURIComponent(architecture), { method: "POST", body }),
      data = await r.json();
    if (!r.ok) throw Error(data.detail);
    startJob(data);
  } catch (e) {
    showError(e.message);
  }
}
function startJob(data) {
  activeJob = data.id;
  launchViewer.setFrames([]);
  restoreLatencyChart();
  $("#run-summary").hidden = true;
  $("#job-monitor").classList.remove("error");
  localStorage.setItem("prism-last-job", data.id);
  window.dispatchEvent(new CustomEvent('prism:job-started'));
  pollJob();
}
async function pollJob() {
  if (polling || !activeJob) return;
  polling = true;
  const id = activeJob;
  try {
    const job = await get("/api/jobs/" + id);
    while (launchViewer.frames.length < job.completed && id === activeJob) {
      launchViewer.append(
        await get(`/api/jobs/${id}/frames/${launchViewer.frames.length}`),
      );
    }
    if (id !== activeJob) return;
    const terminal = [
      "complete",
      "failed",
      "cancelled",
      "interrupted",
    ].includes(job.status);
    $("#job-monitor").classList.toggle("error", job.status === "failed");
    $("#job-monitor").innerHTML =
      `${!terminal ? '<button id="cancel-job" class="button">Stop processing</button>' : ""}<strong>${esc(job.status.toUpperCase())}</strong> · ${job.completed} frames · ${fmt(job.elapsed_seconds, 1)} s · <b>${fmt(job.processing_fps, 2)} FPS processing</b>${job.error ? "<br>" + esc(job.error) : ""}<br><small>${job.model ? esc(job.model.architecture === 'pointnext_s' ? 'PointNeXt-S' : 'PointNet++') + ' · ' + esc(job.model.device) + " · checkpoint epoch " + job.model.epoch : "Loading checkpoint"} · completed results available for replay</small>`;
    if ($("#cancel-job"))
      $("#cancel-job").onclick = () =>
        fetch(`/api/jobs/${activeJob}/cancel`, { method: "POST" });
    if (terminal && launchViewer.frames.length) renderSummary(job);
    else if (!terminal) setTimeout(pollJob, 800);
  } catch (e) {
    showError(e.message);
  } finally {
    polling = false;
  }
}
function consoleFrame(f) {
  const t = f.timing,
    steps = [
      ["Point cloud / ground / blocks", t.preprocess_ms],
      ["Segmentation network", t.network_ms],
      ["Prediction reassembly", t.reassemble_ms],
      ["Grid + foveation", f.grids.prism.grid_ms],
      ["Object / terrain proposals", t.detection_ms],
      ["Browser draw", launchViewer.renderMs],
    ];
  $("#pipeline-steps").innerHTML = steps
    .map(
      ([n, v], i) =>
        `<div class="pipeline-step"><i>${i + 1}</i><span>${n}</span><b>${fmt(v, 1)}<small> ms</small></b></div>`,
    )
    .join("");
  $("#live-confidence").innerHTML =
    '<div class="rail-heading">CLASS CONFIDENCE</div>' +
    f.weightage
      .map(
        (c) =>
          `<div class="confidence-row"><span>${esc(NAMES[c.class])}</span><div><i style="width:${(c.confidence || 0) * 100}%;background:${COLORS[c.class]}"></i></div><b>${c.confidence == null ? "—" : fmt(c.confidence * 100, 0) + "%"}</b></div>`,
      )
      .join("") +
    `<p class="caption">${fmt(f.uncertain_cells, 0)} cells below 50% confidence</p>`;
  const consoleMetrics = [
    ["Processing rate", fmt(1000 / t.processing_ms, 2) + " FPS"],
    ["Time per frame", fmt(t.processing_ms, 0) + " ms"],
    ["Input points", fmt(f.point_count, 0)],
    ["Active map cells", fmt(f.grids.prism.active_cells, 0)],
    [
      "Mean class confidence",
      fmt(
        f.weightage.reduce((a, c) => a + c.share * (c.confidence || 0), 0) *
          100,
        1,
      ) + "%",
    ],
  ];
  if (f.rss_mb != null && Number.isFinite(Number(f.rss_mb)))
    consoleMetrics.splice(2, 0, ["Process memory", fmt(f.rss_mb, 0) + " MiB"]);
  $("#console-metrics").innerHTML = consoleMetrics
    .map(([k, v]) => `<div><small>${k}</small><b>${v}</b></div>`)
    .join("");
  svgChart(
    $("#latency-chart"),
    [
      {
        name: "Processing",
        color: "#a8d77e",
        points: launchViewer.frames
          .slice(Math.max(0, launchViewer.index - 49), launchViewer.index + 1)
          .map((f, x) => ({ x, y: f.timing.processing_ms })),
      },
    ],
    { ylabel: "ms", xlabel: "frames", xName: "Frame", yName: "ms" },
  );
  renderFeed();
}
function renderFeed() {
  const entries = [];
  launchViewer.frames.forEach((f, i) => {
    for (const b of f.boxes || [])
      if (!b.fallback && b.confidence >= launchViewer.threshold)
        entries.push({ f, i, b });
  });
  $("#feed-count").textContent = `${entries.length} cluster observations`;
  $("#detection-feed").innerHTML =
    entries
      .slice(-80)
      .reverse()
      .map(
        (e, k) =>
          `<button data-entry="${k}"><i style="background:${COLORS[e.b.class]}"></i><b>${e.b.class === 3 ? "Object candidate" : "Static obstacle"}</b><span>${fmt(Math.hypot(...e.b.center.slice(0, 2)), 1)} m</span><span>${fmt(e.b.confidence * 100, 0)}%</span><small>Frame ${e.i + 1}${e.b.trail ? " · displacement " + fmt(e.b.displacement_m, 2) + " m" : ""}</small></button>`,
      )
      .join("") ||
    '<p class="caption">No clustered candidates above the display threshold. Sparse fallback boxes remain visible in the viewport.</p>';
  const selected = entries.slice(-80).reverse();
  $$("#detection-feed button").forEach(
    (b) =>
      (b.onclick = () => {
        const e = selected[+b.dataset.entry];
        launchViewer.setPlaying(false);
        launchViewer.show(e.i);
        launchViewer.selectedBox = e.b;
        launchViewer.draw();
      }),
  );
}
function renderSummary(job) {
  const frames = launchViewer.frames,
    hasRss = frames.some(
      (f) => f.rss_mb != null && Number.isFinite(Number(f.rss_mb)),
    ),
    latencies = frames.map((f) => f.timing.processing_ms).sort((a, b) => a - b),
    middle = Math.floor(latencies.length / 2),
    p50 = latencies.length % 2
      ? latencies[middle]
      : (latencies[middle - 1] + latencies[middle]) / 2;
  const latencyChart = $("#latency-chart"),
    latencyHeading = [...$(".pipeline-rail").querySelectorAll(":scope > .eyebrow")]
      .find((node) => node.textContent.includes("PROCESSING LATENCY"));
  $("#run-summary").hidden = false;
  $("#run-summary").innerHTML =
    `<div class="eyebrow">RUN EVIDENCE / ${esc(job.status.toUpperCase())}</div><h3>${frames.length} scans processed locally.</h3><div class="summary-numbers"><span><b>${fmt(job.processing_fps, 2)} FPS</b> processing rate</span><span><b>${fmt(p50, 0)} ms</b> median per scan</span><span><b>${fmt(job.elapsed_seconds, 1)} s</b> total time</span></div><p class="caption">Processing is measured; replay speed is independent.</p><div class="run-chart-grid"><article class="run-chart-card"><div class="eyebrow">PROCESSING LATENCY · MS</div><div id="latency-chart-slot" class="chart"></div></article>${hasRss ? '<article class="run-chart-card"><div class="eyebrow">PROCESS MEMORY · MiB</div><div id="rss-chart" class="chart"></div></article>' : ''}</div>`;
  const latencySlot = $("#latency-chart-slot");
  if (latencyChart && latencySlot) {
    latencyChart.classList.remove("compact");
    latencySlot.append(latencyChart);
    svgChart(latencyChart, [{
      name: "Processing",
      color: "#a8d77e",
      points: frames.map((f, x) => ({ x, y: f.timing.processing_ms })),
    }], { ylabel: "ms", xlabel: "frame", xName: "Frame", yName: "ms" });
  }
  latencyHeading?.remove();
  if (hasRss) {
    svgChart(
      $("#rss-chart"),
      [
        {
          name: "Process RSS",
          color: "#79cadc",
          points: frames.map((f, x) => ({ x, y: f.rss_mb ?? null })),
        },
      ],
      {
        ylabel: "MiB",
        xlabel: "frame",
        xName: "Frame",
        yName: "MiB",
        area: true,
      },
    );
  }
}
function restoreLatencyChart() {
  const chart = $("#latency-chart"), rail = $(".pipeline-rail");
  if (!chart || !rail || rail.contains(chart)) return;
  chart.classList.add("compact");
  const heading = document.createElement("div");
  heading.className = "eyebrow";
  heading.textContent = "PROCESSING LATENCY / MS";
  rail.append(heading, chart);
}
function route() {
  const target = "dashboard";
  document.body.dataset.route = target;
  $$(".page").forEach((p) => (p.hidden = false));
  setTimeout(() => { benchViewer?.draw(); launchViewer?.draw(); }, 50);
  window.dispatchEvent(new CustomEvent("prism:route-changed", { detail: { route: target } }));
}
// Keep section IDs alive for existing render hooks; the composer places their
// contents into one simultaneous dashboard grid.
const mainContent = $("main");
mainContent.append($("#benchmark"), $("#readme"), $("#launch"));
$$('a[href^="/"]').forEach(
  (a) =>
    (a.onclick = (e) => {
      if (e.ctrlKey || e.metaKey || a.hasAttribute("download")) return;
      e.preventDefault();
      const path = new URL(a.href, location.href).pathname;
      const target = path === "/benchmark"
        ? document.querySelector(".dashboard-map-card")
        : path === "/launch"
          ? document.querySelector(".dashboard-process-card")
          : path === "/"
            ? document.querySelector(".dashboard-map-card")
            : document.querySelector(".dashboard-model-card");
      target?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    }),
);
benchViewer = new Viewer($("#benchmark-viewer"));
launchViewer = new Viewer($("#launch-viewer"), true);
const processAction = $(".hero .button.primary"),
  downloadAction = $(".hero a[download]");
processAction?.remove();
if (downloadAction) {
  const identity = $("#readme > .eyebrow"),
    headerLine = document.createElement("div"),
    downloadGroup = document.createElement("div");
  headerLine.className = "readme-headerline";
  downloadGroup.className = "model-downloads";
  downloadGroup.id = "edge-model-downloads";
  downloadAction.remove();
  if (identity) {
    identity.before(headerLine);
    headerLine.append(identity, downloadGroup);
  } else $("#readme")?.append(downloadGroup);
}
launchViewer.onFrame = consoleFrame;
window.PrismRuntime = Object.freeze({
  $,
  $$,
  COLORS,
  NAMES,
  fmt,
  esc,
  svgChart,
  Viewer,
  benchViewer,
  launchViewer,
  modeNames,
  modeColors,
});
route();
$$(".modebar button").forEach(
  (b) =>
    (b.onclick = () => {
      $$(".modebar button").forEach((x) => {
        x.classList.toggle("active", x === b);
        x.setAttribute("aria-selected", x === b);
      });
      benchViewer.setMode(b.dataset.mode);
    }),
);
$$("[data-source]").forEach(
  (b) =>
    (b.onclick = () => {
      $$("[data-source]").forEach((x) => x.classList.toggle("active", x === b));
      $("#preset-list").hidden = b.dataset.source !== "presets";
      $("#upload-controls").hidden = b.dataset.source !== "upload";
      $("#sample-button").hidden = b.dataset.source !== "presets";
    }),
);
$("#confidence-filter").oninput = (e) => {
  launchViewer.threshold = +e.target.value / 100;
  $("#confidence-value").textContent = e.target.value + "%";
  launchViewer.draw();
  renderFeed();
};
$("#upload-files").onchange = (e) => beginFiles(e.target.files);
$("#upload-folder").onchange = (e) => beginFiles(e.target.files);
const drop = $(".drop-zone");
drop.ondragover = (e) => {
  e.preventDefault();
  drop.classList.add("dragover");
};
drop.ondragleave = () => drop.classList.remove("dragover");
drop.ondrop = (e) => {
  e.preventDefault();
  drop.classList.remove("dragover");
  beginFiles(e.dataTransfer.files);
};
$("#sample-button").onclick = async (e) => {
  e.target.disabled = true;
  try {
    const architecture = document.querySelector('#architecture-select')?.value || 'pointnet2';
    const r = await fetch("/api/sample?chunk=" + selectedPreset + '&architecture=' + encodeURIComponent(architecture), {
        method: "POST",
      }),
      d = await r.json();
    if (!r.ok) throw Error(d.detail);
    startJob(d);
  } catch (e) {
    showError(e.message);
  } finally {
    $("#sample-button").disabled = false;
  }
};
get("/api/presets")
  .then((items) => {
    $("#preset-list").innerHTML = items
      .map(
        (p, i) =>
          `<button class="preset ${i === 0 ? "active" : ""}" data-preset="${p.id}"><span class="preset-icon">${String(i + 1).padStart(2, "0")}</span><span><b>${esc(p.name)}</b><small>${p.frames} real scans · frames ${p.start}–${p.end}</small></span></button>`,
      )
      .join("");
    $$(".preset").forEach(
      (b) =>
        (b.onclick = () => {
          selectedPreset = +b.dataset.preset;
          $$(".preset").forEach((x) => x.classList.toggle("active", x === b));
          $("#input-validation").textContent =
            items[selectedPreset].frames +
            " source scans ready for new inference";
        }),
    );
  })
  .catch((e) => ($("#preset-list").textContent = e.message));
get("/api/evidence")
  .then(renderEvidence)
  .catch((e) => {
    $("#training-note").textContent = e.message;
    $("#benchmark-status").textContent = "Local service unavailable.";
  });
import('/assets/features/models.js?v=20260928-spa15').then(({setupModels}) => setupModels()).catch(console.error);
const previousJob = localStorage.getItem("prism-last-job");
if (previousJob) {
  activeJob = previousJob;
  pollJob();
}





