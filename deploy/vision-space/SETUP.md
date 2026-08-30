# Deploying the SolaraX Vision API (M5)

Two jobs: **(A)** host the API on a public HTTPS URL, **(B)** let the deployed
dashboard call it. The CORS code change is already done in `pipeline/vision_api.py`
(env-driven allow-list); the rest is below.

Prerequisite: the repo must be **public** on GitHub (it is), because the Space
build clones it anonymously.

---

## A. Host the API on a Hugging Face Space

### 1. Push the CORS change first

`pipeline/vision_api.py` now reads `VISION_ALLOWED_ORIGINS` and already defaults to
allowing `https://solara-x-inky.vercel.app`. Commit and push it to `main` so the
Space build picks it up:

```
git add pipeline/vision_api.py deploy/vision-space/
git commit -m "feat(m5): env-driven CORS + Hugging Face Space deploy config"
git push
```

### 2. Create the Space

1. Go to <https://huggingface.co/new-space> (free account, sign up if needed).
2. **Owner**: you. **Space name**: `solarax-vision`.
3. **License**: mit (or leave blank).
4. **SDK**: choose **Docker** → **Blank**.
5. **Hardware**: `CPU basic` (free). **Visibility**: Public.
6. Create.

### 3. Add two files to the Space

The Space has its own git repo. You only need `Dockerfile` and `README.md` in it —
both are in this folder. Two ways:

**Web UI (easiest):**
- On the Space page → **Files** → **Add file** → **Upload files**.
- Upload `deploy/vision-space/Dockerfile` and `deploy/vision-space/README.md`
  (rename each to sit at the Space root as `Dockerfile` and `README.md`).
- Commit.

**Git:**
```
git clone https://huggingface.co/spaces/<your-user>/solarax-vision
cd solarax-vision
cp /path/to/SolaraX/deploy/vision-space/Dockerfile .
cp /path/to/SolaraX/deploy/vision-space/README.md .
git add . && git commit -m "vision api" && git push
```

### 4. Wait for the build

The Space builds automatically (~5–10 min the first time — torch is a big
download). Watch the **Logs** tab. When it says the container is running:

```
curl https://<your-user>-solarax-vision.hf.space/health
# -> {"status":"ok"}
```

Test a real prediction with any thermal crop from `data/raw/defects/test/`:

```
curl -X POST https://<your-user>-solarax-vision.hf.space/vision/predict \
  -F "image=@data/raw/defects/test/Cell/4847.jpg"
```

### 5. (optional) Lock down CORS from the Space settings

Space → **Settings** → **Variables and secrets** → new **Variable**:

- Name: `VISION_ALLOWED_ORIGINS`
- Value: `https://solara-x-inky.vercel.app,http://localhost:5173`

This overrides the code default. Restart the Space to apply.

---

## B. Point the dashboard at it  (this part is D's — Vercel owner)

Give D the Space URL. D then:

1. Vercel → the SolaraX project → **Settings → Environment Variables**.
2. Add: `VITE_VISION_API_URL` = `https://<your-user>-solarax-vision.hf.space`
   — scope **Production** (add **Preview** too if you want it on branch deploys).
   **No trailing slash. No API key — it's just the URL.**
3. **Redeploy** — Deployments tab → latest → ⋯ → **Redeploy**. Vite bakes env
   vars in at build time, so a redeploy is required; a restart is not enough.

---

## C. Verify end to end

Open `https://solara-x-inky.vercel.app/site/S-1276`, scroll to the bottom.
"Computer vision evidence" should now render. Upload a thermal image → a defect
class and confidence come back.

Then update the note in `DEPLOY.md` ("The vision service — leave
`VITE_VISION_API_URL` unset") so it reflects that the service is now deployed.

---

## Rollback

To hide the panel again: D removes `VITE_VISION_API_URL` in Vercel and redeploys.
The Space can be paused (Settings → Pause) to stop consuming quota. No other
change needed — the frontend falls back to "the flag stands on electrical
evidence alone".
