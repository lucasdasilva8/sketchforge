from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset.export_feedback import export_feedback
from dataset.generate_synthetic import generate_dataset
from dataset.sketch_dataset import SketchDataset, load_manifest_records
from inference.predictor import SketchCADModel, CHECKPOINT_DIR, CHECKPOINT_PATH

ML_DIR = Path(__file__).resolve().parent
SYNTHETIC_MANIFEST = ML_DIR / "data" / "synthetic" / "manifest.jsonl"
FEEDBACK_MANIFEST = ML_DIR / "data" / "feedback" / "manifest.jsonl"


def train(
    epochs: int = 15,
    batch_size: int = 32,
    lr: float = 1e-3,
    val_split: float = 0.15,
    synthetic_count: int = 2000,
    pretrained: bool = True,
) -> None:
    if not SYNTHETIC_MANIFEST.exists():
        print("Generating synthetic dataset...")
        generate_dataset(synthetic_count)

    export_feedback()

    records = load_manifest_records(SYNTHETIC_MANIFEST, FEEDBACK_MANIFEST)
    if not records:
        raise RuntimeError("No training records found. Run dataset generation first.")

    random.shuffle(records)
    val_size = max(int(len(records) * val_split), 1)
    val_records = records[:val_size]
    train_records = records[val_size:]
    train_ds = SketchDataset(train_records, augment=True)
    val_ds = SketchDataset(val_records, augment=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Training on {device} with {len(train_records)} train / {len(val_records)} val samples")

    model = SketchCADModel(pretrained=pretrained).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    tmpl_loss_fn = nn.CrossEntropyLoss()
    param_loss_fn = nn.MSELoss()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    best_val = float("inf")
    history = []

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        for images, tmpl_labels, param_targets in train_loader:
            images = images.to(device)
            tmpl_labels = tmpl_labels.to(device)
            param_targets = param_targets.to(device)

            optimizer.zero_grad()
            tmpl_logits, params, _conf = model(images)
            loss = tmpl_loss_fn(tmpl_logits, tmpl_labels) + 2.0 * param_loss_fn(params, param_targets)
            loss.backward()
            optimizer.step()

            train_loss += float(loss.item())
            preds = tmpl_logits.argmax(dim=1)
            train_correct += int((preds == tmpl_labels).sum().item())
            train_total += tmpl_labels.size(0)

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, tmpl_labels, param_targets in val_loader:
                images = images.to(device)
                tmpl_labels = tmpl_labels.to(device)
                param_targets = param_targets.to(device)
                tmpl_logits, params, _conf = model(images)
                loss = tmpl_loss_fn(tmpl_logits, tmpl_labels) + 2.0 * param_loss_fn(params, param_targets)
                val_loss += float(loss.item())
                preds = tmpl_logits.argmax(dim=1)
                val_correct += int((preds == tmpl_labels).sum().item())
                val_total += tmpl_labels.size(0)

        scheduler.step()
        train_loss /= max(len(train_loader), 1)
        val_loss /= max(len(val_loader), 1)
        train_acc = train_correct / max(train_total, 1)
        val_acc = val_correct / max(val_total, 1)

        print(
            f"Epoch {epoch + 1}/{epochs} "
            f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
            f"train_acc={train_acc:.2%} val_acc={val_acc:.2%}"
        )
        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_acc": train_acc,
            "val_acc": val_acc,
        })

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            print(f"  Saved best checkpoint → {CHECKPOINT_PATH}")

    metrics_path = CHECKPOINT_DIR / "training_history.json"
    metrics_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"Training complete. Best val loss: {best_val:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SketchForge sketch-to-CAD model")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--synthetic-count", type=int, default=2000)
    parser.add_argument("--no-pretrained", action="store_true")
    args = parser.parse_args()
    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        synthetic_count=args.synthetic_count,
        pretrained=not args.no_pretrained,
    )
