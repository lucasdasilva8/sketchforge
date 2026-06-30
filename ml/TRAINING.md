# Training the SketchForge ML Model

This guide walks you through training the sketch → CADSpec model.

## Quick start (one command)

```bash
cd ~/Projects/sketchforge
./scripts/train_model.sh
```

This will:
1. Generate 2000 synthetic pencil sketches
2. Export any real feedback from your app database
3. Train for 15 epochs
4. Save the best checkpoint to `ml/checkpoints/sketch_cad.pt`

Restart the backend after training to load the new model.

---

## How it works

The model learns two things from each sketch image:

| Output | What it predicts |
|--------|------------------|
| **Template** | box, cylinder, bracket, or profile_extrude |
| **Parameters** | width, depth, height, radius, fillet, wall thickness |

Training data comes from two sources:

1. **Synthetic** — random CAD specs rendered as pencil sketches (`ml/data/synthetic/`)
2. **Feedback** — real sketches + corrected specs from app usage (`ml/data/feedback/`)

Every time you use the app and apply feedback, that correction becomes training data automatically on the next train run.

---

## Step-by-step

### 1. Activate the Python environment

```bash
cd ~/Projects/sketchforge
source backend/.venv/bin/activate
export PYTHONPATH=ml:backend
```

### 2. Generate synthetic training data

```bash
python ml/dataset/generate_synthetic.py --count 2000
```

Output: `ml/data/synthetic/images/` + `manifest.jsonl`

Increase `--count` for better accuracy (try 5000–10000).

### 3. Export real feedback (optional but valuable)

Use the app locally, upload sketches, apply feedback corrections, then:

```bash
python ml/dataset/export_feedback.py
```

This reads `backend/data/sketchforge.db` and exports sketch images with their corrected CAD specs.

### 4. Train

```bash
python ml/train.py --epochs 15 --batch-size 32
```

Options:
- `--epochs 20` — more training (diminishing returns after ~20)
- `--synthetic-count 5000` — regenerate more synthetic data first
- `--lr 0.0005` — lower learning rate for fine-tuning

### 5. Evaluate

```bash
python ml/evaluate.py
```

Target metrics on synthetic data:
- Template accuracy: **>85%**
- Val loss: **<0.5**

### 6. Restart backend

```bash
cd backend && ./run.sh
```

---

## Improving accuracy further

### Use more synthetic data
```bash
python ml/dataset/generate_synthetic.py --count 10000
python ml/train.py --epochs 20
```

### Collect real sketches
The biggest improvement comes from real hand-drawn sketches:
1. Draw 20–50 product sketches on paper
2. Photograph and upload them in the app
3. Fix results with feedback
4. Re-run `./scripts/train_model.sh`

### Fusion 360 Gallery (advanced)
For research-grade results, download the [Fusion 360 Gallery](https://github.com/AutodeskAILab/Fusion360GalleryDataset) and extend `ml/notebooks/01_dataset_exploration.ipynb` to convert CAD sequences into SketchForge templates.

---

## File reference

| File | Purpose |
|------|---------|
| `ml/dataset/generate_synthetic.py` | Create synthetic sketch images |
| `ml/dataset/export_feedback.py` | Export real corrections from SQLite |
| `ml/dataset/sketch_renderer.py` | Pencil-style sketch rendering |
| `ml/dataset/param_codec.py` | Parameter encoding (shared with inference) |
| `ml/train.py` | Training loop |
| `ml/evaluate.py` | Evaluation metrics |
| `ml/checkpoints/sketch_cad.pt` | Saved model weights |
| `ml/inference/predictor.py` | Runtime inference |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named dataset` | Run from project root with `export PYTHONPATH=ml:backend` |
| Training is slow | Normal on CPU; uses Apple MPS GPU if available |
| Low accuracy on real sketches | Add more real feedback data via the app |
| Model not used by API | Restart backend; checkpoint must exist at `ml/checkpoints/sketch_cad.pt` |
