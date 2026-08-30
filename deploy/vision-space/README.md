---
title: SolaraX Vision API
emoji: 🔆
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# SolaraX Vision API

Module 5 (Drone & Visual Verification) for the SolaraX dashboard.

A YOLOv8n-cls thermal-defect classifier, served as:

- `GET  /health`          — liveness check, returns `{"status": "ok"}`
- `POST /vision/predict`   — multipart form field `image`; returns an `evidence`
  object with `defect_class`, `confidence`, and honest `data_status: SIMULATED`.

This is a **verification layer, not the product's pitch**. The fleet-data
detector (Modules 2–3) is what flags a site; this only adds a picture once a
technician is on the roof. Source and context in the main repo:
<https://github.com/cindyyy11/SolaraX>

## Deploy notes

- Built from the public repo by `Dockerfile` — see `deploy/vision-space/` there.
- Set `VISION_ALLOWED_ORIGINS` (Space → Settings → Variables) to override the CORS
  allow-list without a code change, e.g.
  `https://solara-x-inky.vercel.app,http://localhost:5173`.
- Free CPU Spaces sleep after ~48h idle; first request after a sleep cold-starts
  in 30–60s. Hit `/health` a few minutes before a demo to wake it.
