"use strict";
{
  // Extend the existing viewers; their upload, timeline and job controls remain shared.
  const runtime = window.PrismRuntime;
  if (!runtime) throw new Error("PRISM runtime interface is unavailable");
  const {
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
  } = runtime;
  const browserSamples = [];
  let latestGridEvidence = null;
  let latestComputeProfile = null;
  const originalDraw = Viewer.prototype.draw;
  Viewer.prototype.draw = function () {
    const tick = performance.now();
    if (this.mode === "quad" && this.quad) {
      ["raw", "semantic", "voxel", "prism"].forEach((m, i) =>
        this.drawScene(this.quad.querySelectorAll("canvas")[i], m),
      );
    } else originalDraw.call(this);
    const ms = performance.now() - tick;
    if (this.frame && !this.container.closest("[hidden]"))
      browserSamples.push(ms);
    if (browserSamples.length > 500) browserSamples.shift();
    const f = this.frame;
    if (!f) return;
    const a = this.fusion?.uniform || f.grids.uniform,
      b = this.fusion?.prism || f.grids.prism;
    const cut = 100 * (1 - b.active_cells / a.active_cells);
    const meter = this.container.querySelector(".allocation-meter");
    if (meter)
      meter.innerHTML = `<div class="allocation-summary"><small>THIS FRAME · CELL ALLOCATION</small><strong>${fmt(Math.abs(cut), 1)}% <span>${cut >= 0 ? "fewer" : "more"} cells</span></strong></div><div class="allocation-bars"><div class="allocation-row"><span>UNIFORM</span><i style="width:100%"></i><b>${fmt(a.active_cells, 0)}</b></div><div class="allocation-row"><span>PRISM</span><i class="adaptive" style="width:${Math.min(100, (b.active_cells / a.active_cells) * 100)}%"></i><b>${fmt(b.active_cells, 0)}</b></div></div><div class="allocation-storage"><small>LEAF STORAGE</small><b>${fmt(a.bytes / 1048576, 2)} → ${fmt(b.bytes / 1048576, 2)} MiB</b></div>`;
    const turn = this.fusion?.heading ?? f.heading ?? 0;
    const label = this.container.querySelector(".turn-label");
    if (label)
      label.textContent =
        Math.abs(turn) < 0.01
          ? "STRAIGHT"
          : `TURN ${turn < 0 ? "RIGHT" : "LEFT"} · ${fmt((Math.abs(turn) * 180) / Math.PI, 0)}°`;
    const latency = this.container.querySelector(".browser-runtime");
    const sorted = [...browserSamples].sort((a, b) => a - b),
      q = (p) =>
        sorted[
          Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p))
        ];
    if (latency)
      latency.textContent = `Canvas draw P50 / P95 / P99: ${fmt(q(0.5), 1)} / ${fmt(q(0.95), 1)} / ${fmt(q(0.99), 1)} ms · n=${sorted.length} · GPU excluded`;
  };
  function installInspector(viewer) {
    const host = viewer.container;
    host
      .querySelector(".viewport-toolbar > div")
      .insertAdjacentHTML(
        "afterbegin",
        `<label class="inspection-inline">Inspect <select class="diagnostic" aria-label="Map inspection mode"><option value="semantic">Semantic classes</option><option value="confidence">Semantic confidence</option><option value="variance">Elevation variance</option><option value="height">Height discontinuity</option><option value="dynamic">Dynamic-object confidence</option><option value="error">Incorrect cells vs GT</option><option value="unknown">Observed / unobserved</option></select></label>`,
      );
    host
      .querySelector(".viewport-toolbar")
      .insertAdjacentHTML("afterend", `<div class="allocation-meter"></div>`);
    host.querySelector(".diagnostic").onchange = (e) => {
      viewer.diagnostic = e.target.value;
      host.querySelector(".inspection-inline").dataset.scope = {
        semantic:
          "Class palette · dark background is unobserved, never free space",
        confidence: "Red: low → green: high confidence",
        variance: "Green: low → red: ≥0.1 m² height variance",
        height:
          "Green: level → red: ≥0.5m vertical span (not a learned hazard)",
        dynamic: "Green: high object-class confidence · grey: other classes",
        error:
          "Green: correct · red: wrong majority cell label · grey: GT unavailable",
        unknown: "Grey: observed cells · dark: unobserved (not free space)",
      }[viewer.diagnostic];
      viewer.draw();
    };
    host
      .querySelector(".fusion-controls")
      .insertAdjacentHTML(
        "beforeend",
        `<label class="control-card heading-card"><span>FOCUS DIRECTION</span><output class="turn-label">STRAIGHT</output><input class="heading-input" aria-label="Fovea heading in degrees" type="range" min="-180" max="180" value="0"><div class="range-hints"><span>LEFT</span><span>STRAIGHT</span><span>RIGHT</span></div><small>Choose where the high-detail focus points.</small></label>`,
      );
    host.querySelector(".heading-input").oninput = (e) => {
      const degrees = +e.target.value;
      viewer.foveaHeading = (-degrees * Math.PI) / 180;
      host.querySelector(".turn-label").textContent =
        degrees === 0
          ? "STRAIGHT"
          : `TURN ${degrees < 0 ? "LEFT" : "RIGHT"} · ${Math.abs(degrees)}°`;
      viewer.setPlaying(false);
      clearTimeout(viewer.debounce);
      host.querySelector(".fusion-state").textContent =
        "Rebuilding attention field…";
      viewer.debounce = setTimeout(() => viewer.regrid(), 140);
    };
    host.insertAdjacentHTML(
      "beforeend",
      '<div class="semantic-key"><span><i style="background:#a9ad86"></i>Drivable</span><span><i style="background:#b6a08a"></i>Non-drivable terrain</span><span><i style="background:#cfa675"></i>Static obstacles</span><span><i style="background:#83b0be"></i>Dynamic-object semantic segmentation</span></div><div class="zone-key"><b>Resolution zones</b><span>Near <strong>5 cm</strong> / 0–10m</span><span>Mid <strong>10 cm</strong> / 10–25m</span><span>Far <strong>25 cm</strong> / 25–60m</span><span>Horizon <strong>50 cm</strong> / 60–100m</span></div><p class="caption">Cell size follows distance; complex regions can refine further.</p><p class="browser-runtime caption"></p>',
    );
    if (!viewer.single) {
      const el = document.createElement("div");
      el.className = "quad-views";
      el.innerHTML = [
        ["RAW LIDAR", "Observed returns"],
        ["SEMANTIC SEGMENTATION", "Four trained classes"],
        [
          "DENSE 5 CM VOXEL MAP",
          "Allocated 20 × 20 × 4m crop · occupied surfaces",
        ],
        ["SPARSE ADAPTIVE 2.5D", "Height + class + variable leaf size"],
      ]
        .map(
          ([a, b]) =>
            `<div class="quad-panel"><div><b>${a}</b><small>${b}</small></div><canvas aria-label="${a}"></canvas></div>`,
        )
        .join("");
      host.querySelector(".tvs").after(el);
      viewer.quad = el;
      el.querySelectorAll("canvas").forEach((c) => {
        let x = null;
        c.onpointerdown = (e) => {
          x = e.clientX;
          c.setPointerCapture(e.pointerId);
        };
        c.onpointermove = (e) => {
          if (x !== null && e.buttons) {
            viewer.yaw += (e.clientX - x) * 0.008;
            x = e.clientX;
            viewer.foveaHeading = Math.atan2(
              Math.sin(viewer.yaw),
              Math.cos(viewer.yaw),
            );
            const heading = host.querySelector(".heading-input");
            if (heading)
              heading.value = String((-viewer.foveaHeading * 180) / Math.PI);
            viewer.draw();
          }
        };
        c.onpointerup = () => {
          x = null;
          viewer.setPlaying(false);
          viewer.regrid();
        };
        c.onwheel = (e) => {
          e.preventDefault();
          viewer.zoom = Math.max(
            0.45,
            Math.min(8, viewer.zoom * Math.exp(-e.deltaY * 0.001)),
          );
          viewer.draw();
        };
      });
    }
  }
  installInspector(benchViewer);
  installInspector(launchViewer);
  benchViewer.setMode("resolution");
  $$(".modebar button").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === "resolution");
    b.setAttribute("aria-selected", b.dataset.mode === "resolution");
  });
  const benchmark = document.querySelector('#benchmark');
  const modebar = benchmark.querySelector('.modebar');
  modebar.insertAdjacentHTML('afterend', `<div class="judge-navigation"><div><strong>Same scans. Uniform grid and PRISM.</strong><span id="evidence-scope">Loading validation results…</span><span id="checkpoint-match"></span></div><div class="judge-navigation-actions"><button id="open-evidence" class="button" type="button">Full results</button><button id="open-failures" class="button" type="button">Hard cases</button></div></div><div id="judge-metrics" class="judge-metrics" aria-live="polite"></div><div id="compute-evidence" class="compute-evidence"></div>`);
  const drawer = document.createElement('details');
  drawer.id = 'benchmark-evidence-drawer';
  drawer.className = 'benchmark-evidence-drawer';
  drawer.open = true;
  drawer.innerHTML = '<summary>More results by distance, map policy, hard case and processing time</summary>';
  benchmark.querySelector('#benchmark-viewer').after(drawer);
  [...benchmark.querySelectorAll('.chart-grid, #grid-evidence, #failure-gallery')].forEach((item) => drawer.append(item));
  // A legacy epoch-30 point-level snapshot duplicated the current cell-level
  // ablation table and invited invalid cross-checkpoint comparisons.
  benchmark.querySelector('.table-panel')?.remove();
  const voxelCard = document.querySelector('#voxel-note')?.closest('.panel');
  // Do not leave an empty storage-reference card when no valid 3D baseline is available.
  if (voxelCard && document.querySelector('#voxel-note')?.textContent.trim()) drawer.append(voxelCard);
  else voxelCard?.remove();
  document.querySelector('#open-evidence').onclick = () => { drawer.open = true; drawer.scrollIntoView({behavior:'smooth',block:'start'}); };
  document.querySelector('#open-failures').onclick = () => { drawer.open = true; requestAnimationFrame(() => document.querySelector('#failure-gallery')?.scrollIntoView({behavior:'smooth',block:'start'})); };
  get('/api/compute-evidence').then((profile) => {
    const target = document.querySelector('#compute-evidence');
    if (!target || !profile.reference || !profile.foveated) return;
    latestComputeProfile = profile;
    const before = fmt(profile.reference.network_points, 0), after = fmt(profile.foveated.network_points, 0);
    const pointsMetric = document.querySelector('#metric-network-input');
    if (pointsMetric) pointsMetric.innerHTML = `<small>POINTS PER SCAN</small><strong>${before} <span>→</span> ${after}</strong><em>Processing rate: ${fmt(profile.reference.fps, 2)} to ${fmt(profile.foveated.fps, 2)} scans per second. Test used ${profile.frames} scans.</em>`;
    target.innerHTML = `<b>Separate test with ${profile.frames} scans.</b> It has not been repeated with the current model.`;
  }).catch(() => {});
  import('/assets/features/workspace.js?v=20260928-spa23').then(({arrangeWorkspace}) => arrangeWorkspace({benchViewer, launchViewer})).catch(console.error);
  const runtimeNames = {
    preprocess_ms: "Preprocessing (ms)",
    network_ms: "Segmentation (ms)",
    reassemble_ms: "Reassembly (ms)",
    inference_ms: "Inference total (ms)",
    detection_ms: "Object + terrain proposals (ms)",
    serialization_ms: "Serialization (ms)",
    total_pipeline_ms: "Full backend result (ms)",
    processing_ms: "Processing before serialization (ms)",
    grid_ms: "Adaptive grid (ms)",
    uniform_grid_ms: "Uniform grid (ms)",
    rss_mb: "Process RAM (MiB)",
    gpu_allocated_mb: "GPU allocated (MiB)",
    gpu_reserved_mb: "GPU reserved (MiB)",
    gpu_peak_allocated_mb: "Peak GPU allocated (MiB)",
    gpu_peak_reserved_mb: "Peak GPU reserved (MiB)",
  };
  const percent = (v) => (v == null ? "—" : fmt(v * 100, 2) + "%");
  function fillComputeMetric(profile) {
    const card = document.querySelector('#metric-network-input');
    if (!card || !profile?.reference || !profile?.foveated) return;
    card.innerHTML = `<small>POINTS PER SCAN</small><strong>${fmt(profile.reference.network_points, 0)} <span>→</span> ${fmt(profile.foveated.network_points, 0)}</strong><em>Processing rate: ${fmt(profile.reference.fps, 2)} to ${fmt(profile.foveated.fps, 2)} scans per second. Test used ${profile.frames} scans.</em>`;
  }
  function evidenceTable(headers, rows) {
    return `<div class="evidence-scroll"><table><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((v) => `<td>${v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  function renderGridEvidence(d) {
    if (d.status !== "complete") return;
    latestGridEvidence = d;
    $("#benchmark-status").innerHTML =
      `<strong>${d.frames} validation scans · ${esc(d.hardware)}</strong><span>Checkpoint epoch ${fmt(d.model.epoch, 0)} · ${esc(String(d.model.sha256 || '').slice(0, 12))}</span>`;
    const frontierValues = Object.values(d.modes),
      cellValues = frontierValues.map((v) => v.cells / 1000),
      fpsValues = frontierValues.map((v) => v.fps),
      cellSpan = Math.max(...cellValues) - Math.min(...cellValues),
      fpsSpan = Math.max(...fpsValues) - Math.min(...fpsValues),
      cellStep = cellSpan > 30 ? 10 : 5,
      fpsStep = fpsSpan > 0.2 ? 0.1 : 0.05,
      frontierXMin = Math.floor((Math.min(...cellValues) - cellSpan * 0.12) / cellStep) * cellStep,
      frontierXMax = Math.ceil((Math.max(...cellValues) + cellSpan * 0.12) / cellStep) * cellStep,
      frontierYMin = Math.max(0, Math.floor((Math.min(...fpsValues) - Math.max(fpsSpan * 0.25, fpsStep)) / fpsStep) * fpsStep),
      frontierYMax = Math.ceil((Math.max(...fpsValues) + Math.max(fpsSpan * 0.25, fpsStep)) / fpsStep) * fpsStep;
    svgChart(
      $("#frontier-chart"),
      Object.entries(d.modes).map(([k, v]) => ({
        name: modeNames[k],
        color: modeColors[k],
        points: [{ x: v.cells / 1000, y: v.fps }],
      })),
      {
        scatter: true,
        xmin: frontierXMin,
        xmax: frontierXMax,
        ymin: frontierYMin,
        ymax: frontierYMax,
        xlabel: "active cells (thousands)",
        ylabel: "model + grid FPS",
        ydecimals: 2,
        title: "Five-policy measured efficiency frontier",
      },
    );
    svgChart(
      $("#distance-chart"),
      ["uniform", "prism"].map((k) => ({
        name: modeNames[k],
        color: modeColors[k],
        points: d.modes[k].bands.map((b, i) => ({
          x: i,
          y:
            b.common_5cm_cell.miou == null
              ? null
              : b.common_5cm_cell.miou * 100,
        })),
      })),
      {
        ymax: 100,
        ylabel: "common-cell mIoU (%)",
        xlabel: "distance (m)",
        xticks: ["0–10", "10–25", "25–60", "60–100"].map((label, x) => ({
          label,
          x,
        })),
        title: "GT common-cell accuracy across distance",
      },
    );
    $("#distance-chart").nextElementSibling.textContent =
      "Common occupied 5cm GT cell mIoU. Paired frame confidence intervals are below.";

    const m = d.modes,
      u = m.uniform,
      p = m.prism;
    if (d.chunks) {
      const allTieAtDisplayedPrecision = d.chunks.every((chunk) =>
        chunk.delta.every((value) => value == null || Math.abs(value * 100) < 0.0005),
      );
      if (allTieAtDisplayedPrecision) {
        $("#heatmap").innerHTML =
          '<p class="caption">Across all 10 contiguous intervals of sequence 08, both grids have the same class agreement on shared 5 cm reference cells at the displayed precision. The detailed distance table below compares each grid at its actual resolution.</p>';
        $("#heatmap").nextElementSibling.textContent =
          "Matched-support result · 10 intervals from one validation sequence, not 10 independent datasets.";
      } else {
        $("#heatmap").innerHTML =
          "<table><thead><tr><th>08 interval</th><th>0–10m</th><th>10–25m</th><th>25–60m</th><th>60–100m</th></tr></thead><tbody>" +
          d.chunks
            .map(
              (c, i) =>
                `<tr><td>${i + 1} · n=${c.frames}</td>${c.delta.map((v) => `<td style="background:${v == null ? "#e7edef" : v > 0 ? "#efdec2" : v < 0 ? "#d8e7ed" : "#eef3f0"}">${v == null ? "—" : fmt(v * 100, 3)}</td>`).join("")}</tr>`,
            )
            .join("") +
          "</tbody></table>";
        $("#heatmap").nextElementSibling.textContent =
          "Δ mIoU, PRISM − uniform, in percentage points. Ten intervals from one validation sequence are not ten independent datasets.";
      }
    }

    const cellReduction = 100 * (1 - p.cells / u.cells);
    const score = (v) => v == null ? '—' : fmt(v * 100, 2) + '%';
    const strip = document.querySelector('#judge-metrics');
    if (strip) strip.innerHTML =
      `<div><small>NEAR FIELD MAP AGREEMENT · 0 to 10 m</small><strong>${score(u.bands[0].common_5cm_cell.miou)} <span>→</span> ${score(p.bands[0].common_5cm_cell.miou)}</strong><em>Both maps use the same 5 cm cells.</em></div>` +
      `<div id="metric-network-input"><small>POINTS SENT TO THE NETWORK</small><strong>Measured profile loading…</strong><em>Pre-inference foveation reduces model input</em></div>` +
      `<div><small>GRID STORAGE PER SCAN</small><strong>${fmt(u.bytes / 1048576, 2)} <span>→</span> ${fmt(p.bytes / 1048576, 2)} MiB</strong><em>${fmt(cellReduction, 1)}% fewer cells. ${fmt(u.cells, 0)} compared with ${fmt(p.cells, 0)}.</em></div>` +
      `<div><small>TIME TO PROCESS ONE SCAN</small><strong>${fmt(d.runtime?.total_pipeline_ms?.p50, 0)} ms</strong><em>Typical full processing time. Playback is separate.</em></div>`;
    fillComputeMetric(latestComputeProfile);
    const scope = document.querySelector('#evidence-scope');
    if (scope) scope.textContent = `Tested on Sequence 08. ${d.frames} scans. Model checkpoint ${d.model.epoch}.`;
    get('/api/models').then((catalog) => {
      const current = catalog.models.find((model) => model.id === 'pointnet2');
      const mismatch = current?.sha256 && current.sha256 !== d.model.sha256;
      const badge = document.querySelector('#checkpoint-match');
      if (badge) {
        badge.textContent = mismatch ? `Older result. Current model is epoch ${current.epoch}. Run the test again.` : 'Results use the current PointNet++ model.';
        badge.classList.toggle('stale', Boolean(mismatch));
      }
    }).catch(() => {});
    $("#grid-evidence").innerHTML =
      `<div class="eyebrow">RESULTS FROM ${d.frames} SEQUENCE 08 SCANS</div><h2>What changes with PRISM</h2><p class="evidence-verdict">Near field map agreement is ${percent(p.bands[0].common_5cm_cell.miou)}. PRISM uses ${fmt(cellReduction, 1)}% less grid storage. It takes ${fmt(p.grid_ms, 1)} ms to build the grid compared with ${fmt(u.grid_ms, 1)} ms for the uniform map.</p><p>This test shows a small storage saving with similar near field agreement. Grid building is slower on this computer.</p><p class="caption">Checkpoint epoch ${d.model.epoch}. Hardware: ${esc(d.hardware)}. Full processing time appears below.</p>`;
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      `<p class="caption dynamic-recall-note">Dynamic-object semantic recall on occupied cells: ${percent(p.bands[0].cell.recall[3])} at 0–10 m (${fmt(p.bands[0].cell.labeled_points, 0)} labeled cells) and ${percent(p.bands[3].cell.recall[3])} at 60–100 m (${fmt(p.bands[3].cell.labeled_points, 0)} labeled cells). Near-range class recall is strong; far-range recall is a priority for improvement. These labels classify object semantics and do not track motion.</p>`,
    );
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      evidenceTable(
        [
          "Policy",
          "Near map class agreement · 0–10 m",
          "Far map class agreement · 25–100 m*",
          "Near object-class recall",
          "Occupied cells / scan",
          "Grid storage / scan",
          "Grid build time",
          "Model + grid rate",
        ],
        Object.entries(m).map(([k, v]) => {
          const far = v.bands
            .slice(2)
            .filter((b) => b.common_5cm_cell.miou != null);
          return [
            modeNames[k] || k,
            percent(v.bands[0].common_5cm_cell.miou),
            percent(
              far.length
                ? far.reduce((s, b) => s + b.common_5cm_cell.miou, 0) /
                    far.length
                : null,
            ),
            percent(v.bands[0].common_5cm_cell.recall[3]),
            fmt(v.cells, 0),
            fmt(v.bytes / 1048576, 2),
            fmt(v.grid_ms, 1),
            fmt(v.fps, 2),
          ];
        }),
      ) +
        '<p class="caption">Common occupied 5cm GT cells ensure comparable support. *Far value is the macro-average of populated 25–60m and 60–100m bands.</p>',
    );
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      "<h3>Distance bands · PRISM</h3>" +
        evidenceTable(
          [
            "Band (m)",
          "Class agreement in PRISM cells",
          "Class agreement on shared 5 cm cells",
          "Correct cell labels",
          "Object-class recall",
          "Height difference · mean / RMS / 95th percentile (cm)",
          "Obstacle-class overlap",
          "Fewer leaves than uniform grid",
          ],
          p.bands.map((b, i) => [
            b.distance_m.join("–"),
            percent(b.cell.miou),
            percent(b.common_5cm_cell.miou),
            percent(b.cell.accuracy),
            percent(b.cell.recall[3]),
            ["mae", "rmse", "p95"]
              .map((k) =>
                b.elevation[k] == null ? "—" : fmt(b.elevation[k] * 100, 2),
              )
              .join(" / "),
            percent(b.observed_obstacle_iou),
            u.bands[i].cells
              ? fmt(100 * (1 - b.cells / u.bands[i].cells), 1) + "%"
              : "—",
          ]),
        ),
    );
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      "<details open><summary>Class accuracy by distance · precision, recall and confusion</summary>" +
        p.bands
          .map(
            (b) =>
              `<h4>${b.distance_m.join("–")}m · cells at the grid's actual resolution</h4>` +
              evidenceTable(
                ["Class", "Precision", "Recall", "F1", "IoU"],
                NAMES.map((name, i) => [
                  esc(name),
                  percent(b.cell.precision[i]),
                  percent(b.cell.recall[i]),
                  percent(b.cell.f1[i]),
                  percent(b.cell.iou[i]),
                ]),
              ),
          )
          .join("") +
        "</details>",
    );
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      "<h3>Runtime distribution · warm scans</h3><p>" +
        esc(
          d.runtime_scope ||
            "Single adaptive grid, object clustering and serialization; disk I/O, browser and curb ribbons excluded.",
        ) +
        "</p><p>Cold start + first prediction: " +
        fmt(d.cold_start_ms, 0) +
        " ms; checkpoint load " +
        fmt(d.checkpoint_load_ms, 0) +
        " ms. CPU RAM and GPU allocations include the process/runtime; leaf bytes above do not.</p>" +
        evidenceTable(
          ["Pipeline stage / memory", "Typical · P50", "Slower · P95", "Slowest · P99", "Scans measured"],
          Object.entries(d.runtime).map(([k, v]) => [
            esc(runtimeNames[k] || k),
            fmt(v.p50, 2),
            fmt(v.p95, 2),
            fmt(v.p99, 2),
            fmt(v.n, 0),
          ]),
        ),
    );
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      "<details open><summary>How results vary · confidence intervals, cell sizes and coverage</summary><h4>PRISM compared with uniform · 95% paired confidence intervals</h4>" +
        evidenceTable(
          ["Measure · PRISM minus uniform", "Mean change", "95% lower bound", "95% upper bound"],
          Object.entries(d.paired_ci).map(([k, v]) => {
            const labels = {cells:'Occupied leaves per scan',bytes:'Grid storage per scan (MiB)',grid_ms:'Grid build time (ms)',near_cell_miou:'Near-field class agreement (percentage points)'};
            const scale = k === 'bytes' ? 1 / 1048576 : k === 'near_cell_miou' ? 100 : 1;
            const digits = k === 'cells' ? 0 : 2;
            return [labels[k] || k.replaceAll('_',' '), fmt(v?.delta * scale, digits), fmt(v?.low * scale, digits), fmt(v?.high * scale, digits)];
          }),
        ) +
        evidenceTable(
          ["Band", "5cm cells", "10cm cells", "25cm cells", "50cm cells"],
          p.bands.map((b) => [
            b.distance_m.join("–"),
            ...Object.values(b.histogram).map((v) => fmt(v, 0)),
          ]),
        ) +
        evidenceTable(
          ["Observed leaf area share", "5cm", "10cm", "25cm", "50cm"],
          p.bands.map((b) => {
            const total = Object.values(b.area_m2).reduce((a, c) => a + c, 0);
            return [
              b.distance_m.join("–") + "m",
              ...Object.values(b.area_m2).map((v) =>
                total ? percent(v / total) : "—",
              ),
            ];
          }),
        ) +
        `<p>Untouched sequence ${d.test.sequence}: ${d.test.frames} scans · ${esc(d.test.label_status)} Model + grid P50 / P95 / P99: ${fmt(d.test.pipeline_ms.p50, 1)} / ${fmt(d.test.pipeline_ms.p95, 1)} / ${fmt(d.test.pipeline_ms.p99, 1)} ms.</p>` +
        evidenceTable(
          ["Measured composition stratum", "Frames", "Own-cell mIoU"],
          Object.entries(d.scene_strata).map(([k, v]) => [
            k.replaceAll('-', ' '),
            v.frames,
            percent(v.prism_cell_miou),
          ]),
        ) +
        Object.entries(d.limitations)
          .map(([k, v]) => `<p><b>${esc(({weather_lighting:'Weather and lighting',tracking:'Object motion',curb_height_error:'Curb-height ground truth',occupancy:'Free-space ground truth',elevation:'Elevation reference',scene_types:'Scene categories',coverage:'Validation split',boundary:'Boundary accuracy',temporal:'Across-frame stability'})[k] || k)}</b> — ${esc(v)}</p>`)
          .join("") +
        "</details>",
    );
    if (d.temporal_summary) {
      const availableTemporalRows = Object.entries(d.temporal_summary).filter(([, v]) => v.n > 0);
      const temporalEvidence = availableTemporalRows.length
        ? "Stability uses consecutive pose-aligned scans and matches cell centers within 15 cm. Changes in visibility and moving surfaces can affect these measurements." +
          evidenceTable(
            ["Map statistic", "Mean", "P95", "Pairs"],
            availableTemporalRows.map(([k, v]) => [
              esc(({overlap_fraction:'Cells shared by consecutive scans',semantic_flicker_rate:'Change in predicted classes',resolution_change_rate:'Change in cell size',height_stability_mae_m:'Height change · mean absolute (m)'})[k] || k.replaceAll('_', ' ')),
              fmt(v.mean, 4), fmt(v.p95, 4), v.n,
            ]),
          )
        : "Sequence 08 does not have enough pose-aligned consecutive pairs for a map-stability score. The measured focus-turn grid rebuild below is available independently.";
      $("#grid-evidence").insertAdjacentHTML(
        "beforeend",
        "<details open><summary>Map stability and response when focus turns</summary><p>" + temporalEvidence + "</p>" +
          `<p>Post-turn grid rebuild P50 / P95 / P99: ${fmt(d.turn_response.grid_ms.p50, 1)} / ${fmt(d.turn_response.grid_ms.p95, 1)} / ${fmt(d.turn_response.grid_ms.p99, 1)} ms. Mean changed leaves: ${fmt(d.turn_response.changed_leaves.mean, 0)}.</p><p>${esc(d.turn_response.scope)}</p></details>`,
      );
    }
    $("#grid-evidence").insertAdjacentHTML(
      "beforeend",
      `<p class="caption">Mean refinement operations: ${fmt(p.refinement_ops, 0)}. Points retained inside the supported input range are reassembled; retained across the whole scan: ${percent(p.retained_fraction)}. Mean leaf size in GT-complex / simple regions: ${fmt(p.complex_region_mean_cell_m * 100, 2)} / ${fmt(p.simple_region_mean_cell_m * 100, 2)} cm.</p>`,
    );
    $("#failure-gallery").innerHTML =
      '<div class="eyebrow">GT-AUDITED CHALLENGES</div><h2>Where the model struggles.</h2><p>Each pair uses the same crop: prediction left, SemanticKITTI ground truth right. These are hard examples selected for inspection, not representative scores.</p><div class="failure-cards">' +
      d.failure_gallery
        .map(
          (f, i) =>
            `<article><h3>${esc(f.name)}</h3><small>08/${String(f.frame).padStart(6, "0")} · target error ${percent(f.error_fraction)} · ${f.target_points} target points</small><canvas data-failure="${i}" aria-label="Prediction and ground truth ${esc(f.name)}"></canvas><p>Prediction <span>Ground truth</span></p></article>`,
        )
        .join("") +
      '</div><p class="caption">SemanticKITTI does not annotate curb heights or certify overhang clearance. Those outputs are not presented as validated hazard detection.</p>';
    const drawFailures = () =>
      $$("[data-failure]").forEach((c) => {
        const f = d.failure_gallery[+c.dataset.failure],
          r = c.getBoundingClientRect();
        if (!r.width) return;
        c.width = r.width * 2;
        c.height = 420;
        const ctx = c.getContext("2d");
        ctx.fillStyle = "#253a46";
        ctx.fillRect(0, 0, c.width, c.height);
        for (let side = 0; side < 2; side++)
          for (const p of f.points) {
            ctx.fillStyle = COLORS[p[side ? 4 : 3]] || "#9bacb0";
            ctx.fillRect(
              c.width * (side * 0.5 + 0.25) +
                ((p[1] - f.anchor[1]) * c.width) / 20,
              210 - (p[0] - f.anchor[0]) * 44,
              3,
              3,
            );
          }
        ctx.strokeStyle = "#d8e5e9";
        ctx.beginPath();
        ctx.moveTo(c.width / 2, 0);
        ctx.lineTo(c.width / 2, c.height);
        ctx.stroke();
      });
    new ResizeObserver(drawFailures).observe($("#failure-gallery"));
    drawFailures();
  }
  get("/api/grid-evidence")
    .then(renderGridEvidence)
    .catch((e) => ($("#grid-evidence").textContent = e.message));
  window.addEventListener('prism:evidence-loaded', () => {
    if (latestGridEvidence) renderGridEvidence(latestGridEvidence);
  });
}






