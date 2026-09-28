"""Application service for assembling training and benchmark evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from backend.infrastructure.paths import ProjectPaths, paths


class EvidenceService:
    def __init__(self, project_paths: ProjectPaths = paths):
        self.paths = project_paths

    @staticmethod
    def _load(path: Path, default: Any) -> Any:
        return json.loads(path.read_text()) if path.exists() else default

    def get_evidence(self) -> dict[str, Any]:
        log = self.paths.training_log
        return {
            "training": self._load(self.paths.training_run, {"status": "not trained"}),
            "curve": list(csv.DictReader(log.open())) if log.exists() else [],
            "benchmark": self._load(self.paths.benchmark, None),
            "demo": self._load(self.paths.demo_manifest, None),
        }
