from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from models import CADSpec, ProjectResponse, VersionRecord

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "sketchforge.db"
UPLOADS_DIR = DATA_DIR / "uploads"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sketch_path TEXT,
                current_version INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                cad_spec_json TEXT NOT NULL,
                feedback TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(project_id, version),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_project(name: str) -> str:
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, sketch_path, current_version, created_at) VALUES (?, ?, NULL, 0, ?)",
            (project_id, name, now),
        )
    return project_id


def save_sketch(project_id: str, content: bytes, ext: str) -> str:
    path = UPLOADS_DIR / f"{project_id}{ext}"
    path.write_bytes(content)
    with get_conn() as conn:
        conn.execute(
            "UPDATE projects SET sketch_path = ? WHERE id = ?",
            (str(path), project_id),
        )
    return str(path)


def get_sketch_path(project_id: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sketch_path FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    return row["sketch_path"] if row else None


def add_version(
    project_id: str,
    cad_spec: CADSpec,
    feedback: str | None = None,
) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT current_version FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"Project {project_id} not found")
        new_version = int(row["current_version"]) + 1
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO versions (project_id, version, cad_spec_json, feedback, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                new_version,
                json.dumps(cad_spec.model_dump()),
                feedback,
                cad_spec.source,
                now,
            ),
        )
        conn.execute(
            "UPDATE projects SET current_version = ? WHERE id = ?",
            (new_version, project_id),
        )
    return new_version


def get_project(project_id: str) -> ProjectResponse:
    with get_conn() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if not project:
            raise KeyError(f"Project {project_id} not found")
        version_rows = conn.execute(
            """
            SELECT version, cad_spec_json, feedback, source, created_at
            FROM versions WHERE project_id = ? ORDER BY version ASC
            """,
            (project_id,),
        ).fetchall()

    versions: list[VersionRecord] = []
    current_spec: CADSpec | None = None
    for row in version_rows:
        spec = CADSpec.model_validate_json(row["cad_spec_json"])
        versions.append(
            VersionRecord(
                version=row["version"],
                cad_spec=spec,
                feedback=row["feedback"],
                source=row["source"],
                created_at=row["created_at"],
            )
        )
        current_spec = spec

    return ProjectResponse(
        id=project["id"],
        name=project["name"],
        sketch_path=project["sketch_path"],
        current_version=project["current_version"],
        cad_spec=current_spec,
        versions=versions,
    )


def get_latest_spec(project_id: str) -> CADSpec | None:
    project = get_project(project_id)
    return project.cad_spec
