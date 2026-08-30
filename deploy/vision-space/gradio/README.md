---
title: SolaraX Vision API
emoji: 🔆
colorFrom: yellow
colorTo: red
sdk: gradio
app_file: app.py
pinned: false
short_description: M5 thermal-defect classifier for the SolaraX dashboard
---

# SolaraX Vision API

Module 5 (Drone & Visual Verification) for the SolaraX dashboard — a YOLOv8n-cls
thermal-defect classifier.

- `GET  /health`          — liveness check
- `POST /vision/predict`  — multipart form field `image`; returns an `evidence`
  object with `defect_class`, `confidence`, `data_status: SIMULATED`
- `GET  /`                — this Gradio upload demo

A **verification layer, not the pitch**. The fleet-data detector (Modules 2–3)
flags a site; this only adds a picture once a technician is on the roof.
Source + context: <https://github.com/cindyyy11/SolaraX>

## Config

- `VISION_ALLOWED_ORIGINS` (Space → Settings → Variables) — comma-separated CORS
  allow-list. Defaults to the dev origins + `https://solara-x-inky.vercel.app`.
- `MODEL_PATH` — defaults to `best.pt` at the Space root.

Free Spaces sleep after ~48h idle; the first request after a sleep cold-starts in
30–60s. Hit `/health` a few minutes before a demo to wake it.
