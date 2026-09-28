"use strict";

function hide(selector) {
  document
    .querySelectorAll(selector)
    .forEach((element) => element.setAttribute("hidden", ""));
}

function replace(selector, text) {
  const element = document.querySelector(selector);
  if (element) element.textContent = text;
}

function hidePanel(selector) {
  document
    .querySelector(selector)
    ?.closest("article, .panel")
    ?.setAttribute("hidden", "");
}

export function curateJudgeView() {
  hide(".screen-rec, footer");
  document.querySelector("#readme")?.classList.add("judge-card");

  const identity = document.querySelector(
    ".readme-headerline > .eyebrow, #readme > .eyebrow",
  );
  if (identity) {
    identity.innerHTML =
      '<span class="sih-laser">SIH26053</span> / PRISM · LIDAR';
  }
  document
    .querySelector("#readme .section-line h2")
    ?.setAttribute("hidden", "");
  replace("#readme .section-line span", "");

  document
    .querySelector("#benchmark .lab-toolbar .tiny")
    ?.setAttribute("hidden", "");

  const modeLabels = [
    "REPRESENTATION",
    "RESOLUTION",
    "FOCUS CONTROL",
    "FOUR VIEWS",
  ];
  document.querySelectorAll(".modebar button b").forEach((label, index) => {
    if (modeLabels[index]) label.textContent = modeLabels[index];
  });
  document.querySelectorAll(".view-title").forEach((title) => {
    if (title.textContent.includes("LIVE FUSION"))
      title.textContent = "ADAPTIVE GRID";
  });

  replace("#launch .workspace-heading h1", "Process a point cloud");
  replace(
    "#launch .workspace-heading p",
    "Choose a trained model and turn raw LiDAR into a map that keeps detail where it matters.",
  );
  document.querySelector("#launch .console-state")?.setAttribute("hidden", "");
  document
    .querySelector("#launch .workspace-heading .eyebrow")
    ?.setAttribute("hidden", "");

  document
    .querySelector("#readme .panel:first-child .eyebrow")
    ?.setAttribute("hidden", "");
  document
    .querySelector("#readme .panel:first-child h3")
    ?.setAttribute("hidden", "");
  document
    .querySelector("#readme .panel:nth-child(2) .eyebrow")
    ?.setAttribute("hidden", "");
  document
    .querySelector("#readme .panel:nth-child(2) h3")
    ?.setAttribute("hidden", "");
  document
    .querySelector("#readme .panel:nth-child(2) .caption")
    ?.setAttribute("hidden", "");

  document.querySelectorAll("#readme .caption").forEach((element) => {
    if (element.textContent.includes("Four abstraction")) {
      element.textContent =
        "PointNet++ MSG · four semantic classes · best validation checkpoint.";
    }
  });
}
