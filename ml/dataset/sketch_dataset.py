"""PyTorch dataset for sketch → CADSpec training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

PREPROCESS = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.RandomApply([transforms.ColorJitter(brightness=0.2, contrast=0.2)], p=0.5),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

PREPROCESS_EVAL = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def load_manifest_records(*manifest_paths: Path) -> List[dict]:
    records: List[dict] = []
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        base = manifest_path.parent
        with manifest_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                record["_base"] = str(base)
                records.append(record)
    return records


class SketchDataset(Dataset):
    def __init__(
        self,
        records: List[dict],
        augment: bool = True,
    ) -> None:
        self.records = records
        self.transform = PREPROCESS if augment else PREPROCESS_EVAL

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        record = self.records[idx]
        image_path = Path(record["_base"]) / record["image"]
        image = Image.open(image_path).convert("RGB")
        tensor = self.transform(image)
        template_id = torch.tensor(int(record["template_id"]), dtype=torch.long)
        params = torch.tensor(record["params"], dtype=torch.float32)
        return tensor, template_id, params
