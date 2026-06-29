from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from inference.predictor import SketchCADModel, CHECKPOINT_DIR, CHECKPOINT_PATH


class SyntheticSketchDataset(Dataset):
    """Minimal synthetic dataset for bootstrapping the ML checkpoint."""

    def __init__(self, size: int = 256) -> None:
        self.size = size

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        template_id = idx % 4
        image = torch.randn(3, 224, 224)
        params = torch.tensor([
            (idx % 10) / 10 - 0.5,
            ((idx + 3) % 10) / 10 - 0.5,
            ((idx + 5) % 10) / 10 - 0.5,
            ((idx + 7) % 10) / 10 - 0.5,
            ((idx + 2) % 5) / 5,
            ((idx + 4) % 8) / 8 - 0.5,
        ], dtype=torch.float32)
        label = torch.tensor(template_id, dtype=torch.long)
        return image, label, params


def train(epochs: int = 3, batch_size: int = 16) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    model = SketchCADModel()
    loader = DataLoader(SyntheticSketchDataset(), batch_size=batch_size, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    tmpl_loss_fn = nn.CrossEntropyLoss()
    param_loss_fn = nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total = 0.0
        for images, tmpl_labels, param_targets in loader:
            optimizer.zero_grad()
            tmpl_logits, params, _conf = model(images)
            loss = tmpl_loss_fn(tmpl_logits, tmpl_labels) + param_loss_fn(params, param_targets)
            loss.backward()
            optimizer.step()
            total += float(loss.item())
        print(f"Epoch {epoch + 1}/{epochs} loss={total / len(loader):.4f}")

    torch.save(model.state_dict(), CHECKPOINT_PATH)
    print(f"Saved checkpoint to {CHECKPOINT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    train(args.epochs, args.batch_size)
