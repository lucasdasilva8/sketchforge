# Training the SketchForge ML Model

This guide walks you through training the sketch → CADSpec model.

## Furniture / chair training

Chair sketches are side elevations (legs, seat, backrest) — not top-down boxes. Use the furniture training script:

```bash
cd ~/Projects/sketchforge
chmod +x scripts/train_furniture.sh
./scripts/train_furniture.sh
```

Defaults: 5000 synthetic samples, **3× chair oversampling**, 20 epochs, **2.5× chair class weight**.

Customize:
```bash
SYNTHETIC_COUNT=8000 CHAIR_MULTIPLIER=4 EPOCHS=25 ./scripts/train_furniture.sh
```

After training, check per-template accuracy (aim for **chair >80%**):
```bash
python ml/evaluate.py
```

**Real sketches help most:** upload chair photos in the app, fix with feedback (“this is a chair”, “ladder-back”), then re-run the script — feedback is merged automatically.

---

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
| **Template** | box, cylinder, bracket, profile_extrude, or **chair** |
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

## Automatic retraining

After you apply feedback in the app, the backend automatically retrains when **3 corrections** have been collected (configurable).

Check status:
```bash
curl http://127.0.0.1:8000/ml/status
```

Environment variables:
- `AUTO_RETRAIN=true` — enable/disable (default: true locally, false on Render)
- `RETRAIN_THRESHOLD=3` — feedback count before retrain
- `INCREMENTAL_EPOCHS=5` — epochs per auto-retrain

On Render, auto-retrain is disabled by default (CPU limits). Retrain locally and push the checkpoint via Git LFS.

---

## Production model (GitHub + Render)

The trained checkpoint `ml/checkpoints/sketch_cad.pt` is tracked with **Git LFS** so Render can use it.

After retraining locally:
```bash
git lfs install
git add ml/checkpoints/sketch_cad.pt
git commit -m "Update ML checkpoint"
git push
```

If no checkpoint exists on first Render deploy, the API runs a short bootstrap train on startup.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named dataset` | Run from project root with `export PYTHONPATH=ml:backend` |
| Training is slow | Normal on CPU; uses Apple MPS GPU if available |
| Low accuracy on real sketches | Add more real feedback data via the app |
| Model not used by API | Restart backend; checkpoint must exist at `ml/checkpoints/sketch_cad.pt` |
