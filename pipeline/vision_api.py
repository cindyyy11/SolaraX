from pathlib import Path
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from pipeline.defect_classifier import classify_defect


app = FastAPI(
    title="SolaraX Vision API",
    version="1.0",
)


# Allow the Vue development server to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
        "class": result["class"],
        "confidence": result["confidence"],
    }