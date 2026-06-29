# SketchForge

Convert hand-drawn product sketches into editable parametric 3D models in the browser, with text-based feedback to iteratively refine results.

## Features

- Upload photos of hand sketches (PNG, JPG, WebP)
- Heuristic + ML sketch analysis → parametric CAD spec
- In-browser 3D editor powered by [replicad](https://replicad.xyz/) (OpenCascade WASM)
- Text feedback loop ("make it taller", "round the corners more")
- Parametric dimension controls
- Export STL and STEP

## Project structure

```
sketchforge/
├── frontend/          # React + Vite + replicad + Three.js
├── backend/           # FastAPI API + SQLite storage
├── ml/                # Training scripts + inference module
├── shared/            # CADSpec JSON schema
└── scripts/           # Setup helpers
```

## Quick start

**Easiest — one command (starts backend + frontend):**

```bash
./scripts/dev.sh
```

Then open **http://127.0.0.1:5173**

### Prerequisites

- **Node.js 18+** — `brew install node`
- **Python 3.9+**

### Manual start (two terminals)

**Terminal 1 — Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the Vite dev server proxies `/api` to port 8000.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `npm: command not found` | Run `brew install node`, then restart your terminal |
| `Failed to fetch` / network error on load | Start the backend first (`./scripts/dev.sh` or `./backend/run.sh`) |
| Blank page | Use http://127.0.0.1:5173 — do not open `index.html` directly in the browser |
| 3D model fails to build | First load downloads ~10MB WASM — wait a few seconds and try uploading again |
| `Module not found` in frontend | Run `cd frontend && npm install` |

### 3. Optional ML checkpoint

```bash
python ml/train.py --epochs 3
```

## CADSpec format

All subsystems share a parametric JSON schema defined in [`shared/cad_spec.schema.json`](shared/cad_spec.schema.json). Models are built from sketch profiles + operations (extrude, fillet, revolve), not raw meshes.

## Supported templates (v1)

- **box** — rectangular enclosure
- **cylinder** — round forms (vases, knobs)
- **profile_extrude** — custom 2D profile extruded
- **bracket** — L-shaped bracket

## Deployment

See [DEPLOY.md](DEPLOY.md) for GitHub Pages + Render setup.

## License

MIT
