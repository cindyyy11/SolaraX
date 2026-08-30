# SolaraX Vision API — Hugging Face Space (Docker SDK)
#
# This file is the ONLY thing (with README.md) that lives in the Space's own git
# repo. It builds the M5 defect-classifier service straight from the public
# GitHub repo, so there are no copied source files to keep in sync.
#
# Hugging Face Spaces serve on port 7860.

FROM python:3.12-slim

# git         — fetches the pipeline code + model weights, once, below.
# libgl1 /    — OpenCV (a transitive dependency of ultralytics) links against
# libglib2.0-0  these at runtime; without them `import cv2` fails.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Shallow clone of the public repo. To pick up a new commit, trigger a rebuild
# (Space → Settings → "Factory rebuild").
ARG REPO_URL=https://github.com/cindyyy11/SolaraX.git
ARG REPO_REF=main
RUN git clone --depth 1 --branch ${REPO_REF} ${REPO_URL} .

RUN pip install --no-cache-dir -r deploy/vision-space/requirements.txt

# ultralytics and matplotlib insist on a writable config dir. /app is read-only
# for the Space runtime user, so send them to /tmp.
ENV YOLO_CONFIG_DIR=/tmp \
    MPLCONFIGDIR=/tmp \
    HF_HOME=/tmp \
    PYTHONUNBUFFERED=1

EXPOSE 7860

# defect_classifier.py loads YOLO("model/best.pt") relative to the working dir,
# which is /app — the repo root after the clone. Do not change WORKDIR.
CMD ["uvicorn", "pipeline.vision_api:app", "--host", "0.0.0.0", "--port", "7860"]
