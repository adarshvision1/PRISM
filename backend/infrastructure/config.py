"""Central access to repository configuration without changing public behavior."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.labels import ROOT


@dataclass(frozen=True)
class ProjectConfig:
    checkpoint: str
    interim_checkpoint: str
    device: str
    inference_batch_size: int
    max_upload_mb: int
    max_frames: int
    uncertain_threshold: float
    input_points_per_block: int
    far_points_per_block: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024**2

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "ProjectConfig":
        return cls(
            checkpoint=str(values["checkpoint"]),
            interim_checkpoint=str(values["interim_checkpoint"]),
            device=str(values["device"]),
            inference_batch_size=int(values["inference_batch_size"]),
            max_upload_mb=int(values["max_upload_mb"]),
            max_frames=int(values["max_frames"]),
            uncertain_threshold=float(values["uncertain_threshold"]),
            input_points_per_block=int(values["input_points_per_block"]),
            far_points_per_block=int(values["far_points_per_block"]),
        )


def load_config(root: Path = ROOT) -> ProjectConfig:
    """Load the existing config.json using the repository's established root."""
    values = json.loads((root / "config.json").read_text())
    return ProjectConfig.from_mapping(values)


config = load_config()
