import os
from pathlib import Path
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from pipeline.defect_classifier import classify_defect


app = FastAPI(
    title="SolaraX Vision API",
    version="1.0",
)


# Browser origins allowed to call this API.
#
# The defaults cover the Vue dev server and the deployed dashboard. When the API
# is hosted (Hugging Face Space), set VISION_ALLOWED_ORIGINS on the host to a
# comma-separated list to override without a code change. The regex additionally
# lets Vercel preview deployments through, whose subdomain changes per branch.
_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://solara-x-inky.vercel.app",
]

_allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "VISION_ALLOWED_ORIGINS",
        ",".join(_DEFAULT_ALLOWED_ORIGINS),
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/vision/predict")
async def predict_defect(
    image: UploadFile = File(...)
):
    # Keep the original file extension such as .jpg or .png
    suffix = Path(image.filename or "image.jpg").suffix

    # Save the uploaded image temporarily
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:

        contents = await image.read()
        temp_file.write(contents)

        temp_path = temp_file.name

    # Run your trained YOLO model
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