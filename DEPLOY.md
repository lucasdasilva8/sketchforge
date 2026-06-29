# Deployment Guide

Public URL after setup: **https://lucasdasilva8.github.io/sketchforge/**

The app needs two parts:
- **Frontend** → GitHub Pages (https://lucasdasilva8.github.io/sketchforge/)
- **Backend API** → Render (https://sketchforge-api.onrender.com)

---

## Part 1: GitHub Pages (frontend)

The repo includes `.github/workflows/deploy-frontend.yml`. On every push to `main`, GitHub builds and deploys the frontend.

### One-time setup

1. Push this repo to GitHub (e.g. `lucasdasilva8/sketchforge`)
2. Open **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**
3. Push to `main`

Update `frontend/public/config.js` with your Render API URL if it differs from the default.

---

## Part 2: Render (backend API)

1. Create a free account at https://render.com
2. Click **New → Blueprint**
3. Connect the GitHub repo
4. Render reads `render.yaml` from the repo root
5. Click **Apply**

Test the API:

```bash
curl https://sketchforge-api.onrender.com/health
```

Note: PyTorch makes the first deploy slow (~10–20 min on free tier).

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to port 8000.

### ML checkpoint (optional)

```bash
cd ml
python train.py --epochs 3
```

This creates `ml/checkpoints/sketch_cad.pt` for ML-backed conversion.

---

## CORS and API URL

- Local dev uses the Vite proxy (`/api`)
- Production uses `frontend/public/config.js` → `window.SKETCHFORGE_API`
