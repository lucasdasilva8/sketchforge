"""Export real user feedback pairs from the SketchForge SQLite database."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
ML_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dataset.param_codec import TEMPLATE_TO_IDX, encode_params
from models import CADSpec

DB_PATH = BACKEND_DIR / "data" / "sketchforge.db"
DEFAULT_OUT = ML_DIR / "data" / "feedback"


def export_feedback(db_path: Path = DB_PATH, output_dir: Path = DEFAULT_OUT) -> int:
    if not db_path.exists():
        print(f"No database found at {db_path}")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT p.id AS project_id, p.sketch_path, v.version, v.cad_spec_json, v.feedback
        FROM versions v
        JOIN projects p ON p.id = v.project_id
        WHERE v.feedback IS NOT NULL AND p.sketch_path IS NOT NULL
        ORDER BY p.id, v.version
        """
    ).fetchall()
    conn.close()

    count = 0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for row in rows:
            sketch_path = Path(row["sketch_path"])
            if not sketch_path.exists():
                continue
            spec = CADSpec.model_validate_json(row["cad_spec_json"])
            image_name = f"{row['project_id']}_v{row['version']}{sketch_path.suffix}"
            dest = images_dir / image_name
            shutil.copy2(sketch_path, dest)
            record = {
                "id": count,
                "image": str(dest.relative_to(output_dir)),
                "template": spec.template,
                "template_id": TEMPLATE_TO_IDX.get(spec.template, 0),
                "params": encode_params(spec.parameters),
                "parameters": spec.parameters,
                "feedback": row["feedback"],
                "project_id": row["project_id"],
                "version": row["version"],
            }
            manifest.write(json.dumps(record) + "\n")
            count += 1

    print(f"Exported {count} feedback samples to {output_dir}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export feedback training data from app database")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    export_feedback(args.db, args.output)
