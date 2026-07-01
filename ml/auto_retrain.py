"""Automatic background retraining when enough feedback is collected."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

ML_DIR = Path(__file__).resolve().parent
STATE_PATH = ML_DIR / "checkpoints" / "auto_retrain_state.json"
CHECKPOINT_PATH = ML_DIR / "checkpoints" / "sketch_cad.pt"

RETRAIN_THRESHOLD = int(os.getenv("RETRAIN_THRESHOLD", "3"))
AUTO_RETRAIN = os.getenv("AUTO_RETRAIN", "true").lower() in {"1", "true", "yes"}
INCREMENTAL_EPOCHS = int(os.getenv("INCREMENTAL_EPOCHS", "5"))
INCREMENTAL_SYNTHETIC = int(os.getenv("INCREMENTAL_SYNTHETIC", "1500"))

_lock = threading.Lock()
_status: Dict[str, Any] = {
    "enabled": AUTO_RETRAIN,
    "training": False,
    "pending_feedback": 0,
    "last_train_at": None,
    "last_result": None,
    "last_error": None,
}


def _load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"feedback_since_train": 0, "last_train_at": None, "total_trains": 0}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_status() -> Dict[str, Any]:
    with _lock:
        state = _load_state()
        return {
            **_status,
            "pending_feedback": state.get("feedback_since_train", 0),
            "threshold": RETRAIN_THRESHOLD,
            "checkpoint_exists": CHECKPOINT_PATH.exists(),
            "total_trains": state.get("total_trains", 0),
            "last_train_at": state.get("last_train_at"),
        }


def notify_feedback_saved() -> None:
    """Call after a feedback version is stored in the database."""
    if not AUTO_RETRAIN:
        return

    with _lock:
        if _status["training"]:
            return
        state = _load_state()
        state["feedback_since_train"] = int(state.get("feedback_since_train", 0)) + 1
        _save_state(state)
        _status["pending_feedback"] = state["feedback_since_train"]

        if state["feedback_since_train"] < RETRAIN_THRESHOLD:
            return

        state["feedback_since_train"] = 0
        _save_state(state)
        _status["pending_feedback"] = 0
        _status["training"] = True

    thread = threading.Thread(target=_run_training, daemon=True, name="sketchforge-auto-retrain")
    thread.start()


def _run_training() -> None:
    started = time.time()
    try:
        import sys

        backend_dir = ML_DIR.parent / "backend"
        for path in (str(ML_DIR), str(backend_dir)):
            if path not in sys.path:
                sys.path.insert(0, path)

        from dataset.export_feedback import export_feedback
        from train import train

        export_feedback()
        train(
            epochs=INCREMENTAL_EPOCHS,
            batch_size=16,
            synthetic_count=INCREMENTAL_SYNTHETIC,
            chair_multiplier=2.0,
            chair_weight=2.0,
            pretrained=not CHECKPOINT_PATH.exists(),
            fine_tune=CHECKPOINT_PATH.exists(),
            regenerate=True,
        )

        from pipelines.convert import reload_predictor

        reload_predictor()

        with _lock:
            state = _load_state()
            state["last_train_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            state["total_trains"] = int(state.get("total_trains", 0)) + 1
            _save_state(state)
            _status["last_train_at"] = state["last_train_at"]
            _status["last_result"] = {
                "ok": True,
                "duration_sec": round(time.time() - started, 1),
                "epochs": INCREMENTAL_EPOCHS,
            }
            _status["last_error"] = None
    except Exception as exc:
        with _lock:
            _status["last_error"] = str(exc)
            _status["last_result"] = {"ok": False, "error": str(exc)}
    finally:
        with _lock:
            _status["training"] = False
