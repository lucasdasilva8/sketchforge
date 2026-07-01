from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset.param_codec import IDX_TO_TEMPLATE, TEMPLATE_IDS
from dataset.sketch_dataset import SketchDataset, load_manifest_records
from inference.predictor import SketchCADModel, CHECKPOINT_PATH

ML_DIR = Path(__file__).resolve().parent
SYNTHETIC_MANIFEST = ML_DIR / "data" / "synthetic" / "manifest.jsonl"


def evaluate(manifest: Path = SYNTHETIC_MANIFEST) -> None:
    records = load_manifest_records(manifest)
    if not records:
        raise RuntimeError(f"No records in {manifest}")

    dataset = SketchDataset(records, augment=False)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)

    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT_PATH}")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = SketchCADModel(pretrained=False).to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()

    tmpl_loss_fn = nn.CrossEntropyLoss()
    param_loss_fn = nn.MSELoss()
    total_loss = 0.0
    correct = 0
    total = 0
    per_class_correct: dict[str, int] = defaultdict(int)
    per_class_total: dict[str, int] = defaultdict(int)

    with torch.no_grad():
        for images, tmpl_labels, param_targets in loader:
            images = images.to(device)
            tmpl_labels = tmpl_labels.to(device)
            param_targets = param_targets.to(device)
            tmpl_logits, params, _conf = model(images)
            loss = tmpl_loss_fn(tmpl_logits, tmpl_labels) + 2.0 * param_loss_fn(params, param_targets)
            total_loss += float(loss.item())
            preds = tmpl_logits.argmax(dim=1)
            correct += int((preds == tmpl_labels).sum().item())
            total += tmpl_labels.size(0)

            for pred, label in zip(preds.tolist(), tmpl_labels.tolist()):
                name = IDX_TO_TEMPLATE.get(label, "unknown")
                per_class_total[name] += 1
                if pred == label:
                    per_class_correct[name] += 1

    print(f"Samples: {total}")
    print(f"Template accuracy: {correct / max(total, 1):.2%}")
    print(f"Average loss: {total_loss / max(len(loader), 1):.4f}")
    print("\nPer-template accuracy:")
    for name in TEMPLATE_IDS:
        n = per_class_total.get(name, 0)
        if n == 0:
            continue
        acc = per_class_correct[name] / n
        print(f"  {name:16s} {acc:6.1%}  ({per_class_correct[name]}/{n})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=SYNTHETIC_MANIFEST)
    args = parser.parse_args()
    evaluate(args.manifest)
