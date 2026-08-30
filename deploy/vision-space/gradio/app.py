"""
SolaraX Vision API — self-contained Hugging Face Space (Gradio SDK, no card).

Why this exists separately: a Gradio-SDK Space cannot `git clone` the main repo
at build time and cannot import the `pipeline.` package, so this file INLINES the
M5 defect classifier. Canonical version: `pipeline/vision_api.py` +
`pipeline/defect_classifier.py`. Keep in sync by hand.

Serves on port 7860:
  GET  /health          -> {"status": "ok"}
  POST /vision/predict  -> multipart form field `image`; returns {"evidence": {...}}
  GET  /                -> a small Gradio upload UI

How it runs on a Gradio Space: HF's launcher runs `python app.py`. We call
`demo.launch()` ourselves (so HF does NOT also launch and collide on 7860), then
graft the REST routes onto the Gradio app it created. CORS is passed in through
`app_kwargs` because middleware cannot be added after the server has started.

Upload alongside this file: requirements.txt, README.md, best.pt (at the Space
root, or set MODEL_PATH in the Space variables).
"""

import os
import tempfile
import threading
from pathlib import Path

# Ultralytics wants a writable config dir; /home/user/.config is read-only on the
# Space. Point it at /tmp before the import so it doesn't warn on every start.
os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/Ultralytics")

# Force CPU. On ZeroGPU hardware torch reports CUDA as available, but it only
# works inside a @spaces.GPU function — so ultralytics tries cuda:0 outside that
# context and the request 500s. YOLOv8n-cls on CPU is ~15 ms, so hide the GPU.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import gradio as gr
from fastapi import File, UploadFile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from ultralytics import YOLO

# ZeroGPU hardware refuses to start a Space with no @spaces.GPU function. The
# classifier runs on CPU (YOLOv8n-cls is milliseconds), so this probe exists only
# to satisfy that check and is never called. On CPU/Docker hardware the `spaces`
# package is absent and this block is skipped.
try:
    import spaces

    @spaces.GPU
    def _zerogpu_probe():
        return None

except Exception:
    pass


# --- model ---------------------------------------------------------------
MODEL_PATH = os.environ.get("MODEL_PATH", "best.pt")
CONFIDENCE_THRESHOLD = 0.65

model = YOLO(MODEL_PATH)


def classify_defect(image_path: str) -> dict:
    """Classify one thermal solar-module image. Mirrors pipeline/defect_classifier.py."""
    results = model(image_path, device="cpu", verbose=False)
    result = results[0]

    class_id = result.probs.top1
    class_name = result.names[class_id]
    confidence = float(result.probs.top1conf)

    if confidence < CONFIDENCE_THRESHOLD:
        return {"class": "Unknown", "confidence": confidence}

    return {"class": class_name, "confidence": confidence}


# --- REST handlers -----------------------------------------------------
def health():
    return {"status": "ok"}


async def predict_defect(image: UploadFile = File(...)):
    suffix = Path(image.filename or "image.jpg").suffix

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await image.read())
        temp_path = temp_file.name

    result = classify_defect(temp_path)

    return {
        "evidence": {
            "has_imagery": True,
            "defect_class": result["class"],
            "confidence": result["confidence"],
            "model_note": "Fine-tuned YOLOv8n-cls on RaptorMaps infrared module crops",
            "inference_mode": "interactive",
            "data_status": "SIMULATED",
        }
    }


# --- CORS --------------------------------------------------------------
_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://solara-x-inky.vercel.app",
]
_allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "VISION_ALLOWED_ORIGINS", ",".join(_DEFAULT_ALLOWED_ORIGINS)
    ).split(",")
    if origin.strip()
]

_cors = Middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Gradio UI -------------------------------------------------------
def _ui_predict(image_path):
    if not image_path:
        return "Upload a thermal solar-module image."
    result = classify_defect(image_path)
    return "{} - {:.1f}% confidence".format(
        result["class"], result["confidence"] * 100
    )


with gr.Blocks(title="SolaraX Vision API") as demo:
    gr.Markdown(
        "# SolaraX Vision API\n"
        "Module 5 defect classifier for the SolaraX dashboard.\n\n"
        "REST: `GET /health` &nbsp;|&nbsp; `POST /vision/predict` "
        "(multipart form field `image`)."
    )
    _img = gr.Image(type="filepath", label="Thermal module image")
    _out = gr.Textbox(label="Prediction", interactive=False)
    _img.change(_ui_predict, inputs=_img, outputs=_out)


def main():
    port = int(
        os.environ.get("PORT", os.environ.get("GRADIO_SERVER_PORT", 7860))
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        prevent_thread_lock=True,           # returns instead of blocking
        ssr_mode=False,                     # no Node proxy — plain uvicorn on 7860
        app_kwargs={"middleware": [_cors]},  # CORS must be set at app creation
    )

    # Graft the REST routes onto the app Gradio just built. Routes (unlike
    # middleware) can be added after startup — the router is consulted per request.
    demo.app.add_api_route("/health", health, methods=["GET"])
    demo.app.add_api_route("/vision/predict", predict_defect, methods=["POST"])

    # Keep the process alive; the server runs on a background thread.
    threading.Event().wait()


if __name__ == "__main__":
    main()
