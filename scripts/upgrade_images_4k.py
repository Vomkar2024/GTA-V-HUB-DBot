"""Upgrade all vehicle assets to 4K resolution using high-quality Lanczos resampling."""
from __future__ import annotations

import concurrent.futures
import os
import sys
import time
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

TARGET_DIMENSION = 3840


def process_image(image_path: Path) -> tuple[str, bool, tuple[int, int], str]:
    """Upscale a single image to 4K max dimension while preserving aspect ratio and mode."""
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            if max(w, h) >= TARGET_DIMENSION:
                return image_path.name, True, (w, h), "Already 4K"

            if w >= h:
                new_w = TARGET_DIMENSION
                new_h = max(1, round(h * (TARGET_DIMENSION / w)))
            else:
                new_h = TARGET_DIMENSION
                new_w = max(1, round(w * (TARGET_DIMENSION / h)))

            # Use Lanczos resampling for premium scaling quality
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            temp_path = image_path.with_suffix(".tmp.png")
            resized.save(temp_path, format="PNG", compress_level=6)

        os.replace(temp_path, image_path)
        return image_path.name, True, (new_w, new_h), "Success"
    except Exception as exc:
        return image_path.name, False, (0, 0), str(exc)


def upgrade_all_images(assets_dir: Path | str = "assets/images") -> None:
    if Image is None:
        print("Error: The Pillow package is required for upgrade_images_4k.py. Install it with: pip install Pillow")
        sys.exit(1)

    base_dir = Path(assets_dir)
    if not base_dir.is_dir():
        print(f"Error: Directory '{base_dir}' does not exist.")
        sys.exit(1)

    images = sorted(base_dir.glob("*.png"))
    total = len(images)
    print(f"Found {total} PNG images in '{base_dir}'. Upgrading to 4K ({TARGET_DIMENSION}px)...")

    start_time = time.time()
    successful = 0
    failed = 0

    max_workers = os.cpu_count() or 4
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for index, (filename, success, size, msg) in enumerate(
            executor.map(process_image, images), start=1
        ):
            if success:
                successful += 1
            else:
                failed += 1
                print(f"[{index}/{total}] FAILED {filename}: {msg}")

            if index % 100 == 0 or index == total:
                elapsed = time.time() - start_time
                print(f"[{index}/{total}] images processed ({successful} succeeded, {failed} failed) in {elapsed:.1f}s")

    elapsed = time.time() - start_time
    print(f"Finished processing {total} images in {elapsed:.2f}s! ({successful} succeeded, {failed} failed)")


if __name__ == "__main__":
    target_path = Path("assets/images") if len(sys.argv) < 2 else Path(sys.argv[1])
    upgrade_all_images(target_path)

