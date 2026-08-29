"""Manual smoke check for M5's defect classifier. NOT a test.

RENAMED FROM test_cv_model.py, AND THAT IS THE WHOLE POINT. Under its old name
pytest collected it as a test module and ran this file's top-level code at
COLLECTION time. It hard-codes an image path under `data/raw/`, which .gitignore
excludes, so on any machine that had not downloaded the 20,000-image dataset it
raised FileNotFoundError before a single real test executed - and pytest aborts
the whole run on a collection error. The result was that `python -m pytest
pipeline/` ran ZERO of the pipeline's tests while appearing to fail for reasons
nobody could see.

This file still does exactly what its author intended. It is a script you run by
hand against a local image to see that the model loads and predicts:

    python pipeline/cv_smoke_check.py
    python pipeline/cv_smoke_check.py path/to/thermal.jpg

M5 belongs to owner B. Nothing here is changed except the filename, an argument
so the path is not hard-coded, and a readable failure when the image or the
`ultralytics` dependency is absent.
"""

import os
import sys

DEFAULT_IMAGE = os.path.join("data", "raw", "defects", "test", "Hot-Spot", "6739.jpg")


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE

    if not os.path.exists(image_path):
        raise SystemExit(
            "no image at {}\n"
            "data/raw/ is gitignored, so this is expected on a fresh clone.\n"
            "Fetch the dataset first: python pipeline/fetch_defect_dataset.py\n"
            "Or pass an image: python pipeline/cv_smoke_check.py path/to/image.jpg"
            .format(image_path))

    try:
        from defect_classifier import classify_defect
    except ImportError as error:
        raise SystemExit(
            "the classifier could not be imported ({}).\n"
            "It needs ultralytics: pip install -r pipeline/requirements.txt".format(error))

    result = classify_defect(image_path)
    print("Prediction:", result["class"])
    print("Confidence:", round(result["confidence"] * 100, 2), "%")


if __name__ == "__main__":
    main()
