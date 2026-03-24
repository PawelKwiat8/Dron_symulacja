#!/usr/bin/env python3
"""Quick local smoke test for a YOLO .pt model on file or folder."""

from __future__ import annotations

import argparse
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def resolve_images(source: Path) -> list[Path]:
    """Return image list from file or directory input."""
    if source.is_file():
        return [source]

    if source.is_dir():
        candidates = sorted(
            p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
        if candidates:
            return candidates
        raise FileNotFoundError(f"No image files found in directory: {source}")

    raise FileNotFoundError(f"Source path does not exist: {source}")


def output_name(image_path: Path, source_path: Path) -> str:
    """Create stable output filename for single image and folder modes."""
    if source_path.is_file():
        return f"{image_path.stem}_pred.jpg"

    rel = image_path.relative_to(source_path)
    rel_stem = str(rel.with_suffix("")).replace("/", "__")
    return f"{rel_stem}_pred.jpg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run YOLO model on one image or full folder.")
    parser.add_argument("--model", default="yolo/best.pt", help="Path to YOLO .pt model")
    parser.add_argument(
        "--source",
        default="dataset_yolo/images_raw",
        help="Image file or directory with test images",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument(
        "--save-dir",
        default="yolo/test_outputs",
        help="Directory for annotated output images",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Limit number of images when source is a directory (0 = all)",
    )
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError:
        print("Missing dependency: ultralytics. Activate venv and run: pip install ultralytics")
        return 1

    model_path = Path(args.model)
    source_path = Path(args.source)
    save_dir = Path(args.save_dir)

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        return 1

    try:
        image_paths = resolve_images(source_path)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    print(f"Using model: {model_path}")
    print(f"Found images: {len(image_paths)}")

    if args.max_images > 0:
        image_paths = image_paths[: args.max_images]
        print(f"Processing first {len(image_paths)} images (--max-images={args.max_images})")

    model = YOLO(str(model_path))
    save_dir.mkdir(parents=True, exist_ok=True)

    total_boxes = 0
    images_with_detections = 0

    for idx, image_path in enumerate(image_paths, start=1):
        results = model.predict(source=str(image_path), conf=args.conf, verbose=False)
        if not results:
            print(f"[{idx}/{len(image_paths)}] {image_path.name}: no inference output")
            continue

        result = results[0]
        boxes = result.boxes
        n = int(len(boxes)) if boxes is not None else 0
        total_boxes += n
        if n > 0:
            images_with_detections += 1

        out_path = save_dir / output_name(image_path, source_path)
        result.save(filename=str(out_path))
        print(f"[{idx}/{len(image_paths)}] {image_path.name}: detections={n} -> {out_path}")

    print(
        "Summary: "
        f"images={len(image_paths)}, "
        f"with_detections={images_with_detections}, "
        f"total_boxes={total_boxes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
