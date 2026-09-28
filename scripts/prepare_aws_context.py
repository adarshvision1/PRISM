"""Create a minimal, reproducible Docker build context for the PRISM service."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_file(source: Path, destination: Path, required: bool = True) -> bool:
    if not source.is_file():
        if required:
            raise FileNotFoundError(f"Required deployment input is missing: {source.relative_to(ROOT)}")
        return False
    target = destination / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination / source.relative_to(ROOT),
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def build_context(output: Path) -> dict:
    output = output.resolve()
    build_root = (ROOT / ".build").resolve()
    if output == ROOT or output == build_root or build_root not in output.parents:
        raise ValueError(f"Build context must be a child of {build_root}")
    if output.exists():
        if not output.is_dir() or output.is_symlink():
            raise ValueError(f"Build context destination must be a regular directory: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    for name in ("backend", "frontend"):
        copy_tree(ROOT / name, output)
    for name in (
        "Dockerfile",
        "config.json",
        "README.md",
        "requirements.txt",
        "requirements-model.txt",
        "data/pointnet_demo.json",
        "data/pointnet_benchmark.json",
        "data/grid_evidence.json",
        "data/performance_trials.json",
        "data/model_comparison.json",
        "data/training_run.json",
        "data/semantic-kitti.yaml",
        "docs/training_log.csv",
        "vendor/semantic-kitti-LICENSE",
        "data/models/pointnext_s/training.csv",
        "data/models/pointnext_s/training_run.json",
    ):
        copy_file(ROOT / name, output)

    demo = json.loads((ROOT / "data/pointnet_demo.json").read_text(encoding="utf-8"))
    indices = sorted({int(i) for chunk in demo["chunks"] for i in chunk["indices"]})
    frame_ids = sorted({int(i) for chunk in demo["chunks"] for i in chunk["frame_ids"]})
    for index in indices:
        copy_file(ROOT / "data/pointnet_frames" / f"{index:05d}.json", output)
    for frame_id in frame_ids:
        for kind, suffix in (("velodyne", ".bin"), ("labels", ".label")):
            copy_file(ROOT / "data/dataset/sequences/08" / kind / f"{frame_id:06d}{suffix}", output, required=kind == "velodyne")
    for name in ("calib.txt", "poses.txt"):
        copy_file(ROOT / "data/dataset/sequences/08" / name, output, required=name == "calib.txt")

    for name in (
        "backend/model/weights/best.ckpt",
        "backend/model/weights/pointnext_s/best.ckpt",
    ):
        copy_file(ROOT / name, output)
    copy_tree(ROOT / "data/deployment", output)
    (output / "data/jobs").mkdir(parents=True, exist_ok=True)
    (output / "data/jobs/.gitkeep").write_text("", encoding="utf-8")

    manifest = {
        "project": "PRISM Adaptive LiDAR Mapping",
        "container_data": "Selected sequence 08 demo scans only. Training dataset is excluded.",
        "demo_frames": len(indices),
        "source_scans": len(frame_ids),
        "architectures": ["pointnet2", "pointnext_s"],
        "checkpoints": [
            "backend/model/weights/best.ckpt",
            "backend/model/weights/pointnext_s/best.ckpt",
        ],
    }
    (output / "BUILD_CONTEXT.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".build" / "aws-container")
    args = parser.parse_args()
    context = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = build_context(context)
    print(json.dumps({"context": str(context.resolve()), **manifest}, indent=2))


if __name__ == "__main__":
    main()
