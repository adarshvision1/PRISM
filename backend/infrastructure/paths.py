"""Stable filesystem locations used by the runtime and evidence APIs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.labels import ROOT


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = ROOT

    @property
    def frontend_assets(self) -> Path:
        return self.root / "frontend" / "assets"

    @property
    def frontend_index(self) -> Path:
        return self.root / "frontend" / "index.html"

    @property
    def jobs(self) -> Path:
        return self.root / "data" / "jobs"

    @property
    def pointnet_frames(self) -> Path:
        return self.root / "data" / "pointnet_frames"

    @property
    def dataset(self) -> Path:
        return self.root / "data" / "dataset"

    @property
    def demo_manifest(self) -> Path:
        return self.root / "data" / "pointnet_demo.json"

    @property
    def training_run(self) -> Path:
        return self.root / "data" / "training_run.json"

    @property
    def benchmark(self) -> Path:
        return self.root / "data" / "pointnet_benchmark.json"

    @property
    def grid_evidence(self) -> Path:
        return self.root / "data" / "grid_evidence.json"

    @property
    def training_log(self) -> Path:
        return self.root / "docs" / "training_log.csv"

    @property
    def deployment_model(self) -> Path:
        return self.root / "data" / "deployment" / "PRISM-trained-model.zip"


paths = ProjectPaths()
