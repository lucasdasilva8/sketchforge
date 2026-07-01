"""Generate synthetic sketch dataset for model training."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import cv2

from dataset.param_codec import TEMPLATE_TO_IDX, encode_params
from dataset.sketch_renderer import render_spec_sketch
from dataset.spec_factory import GENERATORS, random_spec

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_OUT = DATA_DIR / "synthetic"


def generate_dataset(
    count: int = 2000,
    output_dir: Path = DEFAULT_OUT,
    seed: int = 42,
    chair_multiplier: float = 1.0,
) -> Path:
    random.seed(seed)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"

    templates = list(GENERATORS.keys())
    base_per_template = max(count // len(templates), 1)
    template_counts = {name: base_per_template for name in templates}
    if "chair" in template_counts and chair_multiplier > 1:
        template_counts["chair"] = int(base_per_template * chair_multiplier)

    with manifest_path.open("w", encoding="utf-8") as manifest:
        idx = 0
        for template, n_samples in template_counts.items():
            for _ in range(n_samples):
                spec = random_spec(template)
                image = render_spec_sketch(spec)
                image_name = f"{template}_{idx:05d}.png"
                image_path = images_dir / image_name
                cv2.imwrite(str(image_path), image)

                record = {
                    "id": idx,
                    "image": str(image_path.relative_to(output_dir)),
                    "template": spec.template,
                    "template_id": TEMPLATE_TO_IDX[spec.template],
                    "params": encode_params(spec.parameters),
                    "parameters": spec.parameters,
                }
                manifest.write(json.dumps(record) + "\n")
                idx += 1

    print(f"Generated {idx} samples in {output_dir}")
    if chair_multiplier > 1:
        print(f"  Chair oversample: {chair_multiplier}x ({template_counts.get('chair', 0)} chair sketches)")
    print(f"Manifest: {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic sketch training data")
    parser.add_argument("--count", type=int, default=2000, help="Total number of samples")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--chair-multiplier", type=float, default=1.0, help="Oversample chair sketches (e.g. 3.0)")
    args = parser.parse_args()
    generate_dataset(args.count, args.output, args.seed, args.chair_multiplier)
