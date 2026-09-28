"""Persistence adapter for job records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.infrastructure.paths import paths


class JobRepository:
    def __init__(self, jobs_root: Path = paths.jobs):
        self.jobs_root = jobs_root

    def save(self, folder: Path, record: dict[str, Any]) -> None:
        (folder / "job.json").write_text(json.dumps(record))

    def load(self, job_id: str) -> dict[str, Any] | None:
        path = self.jobs_root / job_id / "job.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
