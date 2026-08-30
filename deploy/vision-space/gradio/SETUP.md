# Deploying the Vision API as a Gradio Space (no payment method needed)

Use this path when the Docker SDK shows "Paid" on your HF account. A Gradio-SDK
Space runs free. Everything is uploaded through the web UI — no git push to the
SolaraX repo.

Files in this folder:

| File | Goes where |
|---|---|
| `app.py` | Space root — the whole service, classifier logic inlined |
| `requirements.txt` | Space root |
| `README.md` | Space root — carries the `sdk: gradio` front-matter |
| `best.pt` | Space root — **copy from `model/best.pt` in the repo** (3 MB) |

---

## 1. Create the Space

1. https://huggingface.co/new-space
2. **Owner**: you · **Space name**: `solarax-vision`
3. **License**: `mit`
4. **SDK**: **Gradio** → **Blank**
5. **Space hardware**: `ZeroGPU` (the only free option offered) — fine, the app
   runs on CPU regardless
6. **Storage**: None
7. **Visibility**: Public
8. Create

## 2. Upload the four files

On the Space page → **Files** → **+ Add file** → **Upload files**.

- Drag in `app.py`, `requirements.txt`, `README.md` from this folder.
- Also upload the model: copy `model/best.pt` from the repo and drag it in as
  `best.pt` (root level — matches `MODEL_PATH` default in `app.py`).
- **Commit changes to `main`**.

The Space rebuilds automatically after each commit. First build ~5–10 min
(torch download). Watch the **Logs** tab.

## 3. Verify

When the Space status badge shows **Running**:

```bash
curl https://<your-hf-username>-solarax-vision.hf.space/health
# -> {"status":"ok"}

curl -X POST https://<your-hf-username>-solarax-vision.hf.space/vision/predict \
  -F "image=@data/raw/defects/test/Cell/4847.jpg"
# -> {"evidence":{"defect_class":"Cell","confidence":0.98, ...}}
```

The Space's own page (the `/` URL) shows a small upload demo too.

### If the build fails on ZeroGPU

Some ZeroGPU Spaces reject apps that never call `@spaces.GPU`. If the logs show a
ZeroGPU/`spaces` error:

- Space → **Settings** → **Space hardware** → switch to **CPU basic** if it's
  available to you, or
- keep ZeroGPU and add `import spaces` at the top of `app.py` plus a dummy
  `@spaces.GPU` function that is never called — usually enough to satisfy the
  check. Ask if you hit this.

## 4. (optional) Pin the CORS origins

Space → **Settings** → **Variables and secrets** → new **Variable**:

- `VISION_ALLOWED_ORIGINS` = `https://solara-x-inky.vercel.app,http://localhost:5173`

Restart the Space.

## 5. Hand the URL to D (Vercel owner)

> Vision API is live at `https://<your-hf-username>-solarax-vision.hf.space`.
> To switch on the CV panel: Vercel → SolaraX project → Settings → Environment
> Variables → add `VITE_VISION_API_URL` = that URL (Production scope, no trailing
> slash) → Deployments → Redeploy.

Only D can do this — it needs Vercel access, and Vite bakes the value in at build
time so a redeploy is required.

## 6. Verify end to end

`https://solara-x-inky.vercel.app/site/S-1276` → scroll to the bottom →
"Computer vision evidence" panel → upload a thermal image → prediction returns.

## 7. Update docs

`DEPLOY.md` still says "leave `VITE_VISION_API_URL` unset". Once it's live, change
that section to record the Space URL and that the var is now set.

---

## Rollback

D removes `VITE_VISION_API_URL` in Vercel and redeploys → panel hidden again,
frontend falls back to "the flag stands on electrical evidence alone". Pause the
Space (Settings → Pause) to stop it consuming quota.
