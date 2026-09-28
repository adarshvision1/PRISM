"""Application service for adaptive scene regridding."""
from __future__ import annotations

from typing import Any

from backend.application.scene_service import fusion


class FusionService:
    def regrid(
        self,
        manager: Any,
        demo_index: int,
        speed_kmh: float,
        job_id: str | None,
        frame_index: int,
        heading: float,
    ) -> Any:
        return fusion(
            manager,
            demo_index,
            speed_kmh,
            job_id,
            frame_index,
            heading=heading,
        )
