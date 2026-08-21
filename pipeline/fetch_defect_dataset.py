"""Pull the RaptorMaps infrared solar module dataset and reshape it for M5.

WHY THIS EXISTS. M5 was recorded as blocked on dataset availability, not effort:
no surveyed candidate was simultaneously thermal, labelled and permissively
licensed. That survey missed one. RaptorMaps publish 20,000 labelled infrared
module crops under the MIT licence (verified: LICENSE, "Copyright (c) 2020
Raptor Maps, Inc."). It is the only openly licensed set that is thermal AND
carries class labels, which makes it the only viable input rather than the most
convenient one.

It also settles the shape argument. The labels are class names with no bounding
boxes, which is what docs/Schema.md section 8.8 asks for: a defect_class string
and a confidence. This is a classification problem. Whoever trains on it should
reach for yolov8n-cls, not YOLOv8 detection.

WHAT THIS IS NOT. It is not Malaysian data, and it is not rooftop data. These
are crops from utility-scale flights, so a model trained here is labelled
SIMULATED per the two-layer vocabulary in CLAUDE.md — real method, public
sample input. The honest defence is that at cropped-module scale a hot cell
looks the same on a rooftop as on a 50 MW plot; the honest admission is that
this is an argument, not a measurement. Say both.

It is also not a detector. M3 decides where to go. This produces corroborating
evidence once a site is already flagged electrically.

Run:
    python pipeline/fetch_defect_dataset.py             # download + reshape
    python pipeline/fetch_defect_dataset.py --dry-run   # report, write nothing
    python pipeline/fetch_defect_dataset.py --summary   # class table only

Output: data/raw/defects/{train,valid,test}/{class_name}/*.jpg
        (under data/raw/, which .gitignore already excludes — 20k images is far
        past the ~1 MB per-file rule that governs what may be committed)
"""

import argparse
import json
import os
import random
import shutil
import urllib.request
import zipfile

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIRECTORY = os.path.join(REPOSITORY_ROOT, "data", "raw")
ARCHIVE_PATH = os.path.join(RAW_DIRECTORY, "infrared_solar_modules.zip")
EXTRACT_DIRECTORY = os.path.join(RAW_DIRECTORY, "infrared_solar_modules")
OUTPUT_DIRECTORY = os.path.join(RAW_DIRECTORY, "defects")

# --- Source -----------------------------------------------------------------
# MIT licensed. Verified 22 Aug 2026 against the repository LICENSE file.

DATASET_URL = (
    "https://raw.githubusercontent.com/RaptorMaps/InfraredSolarModules/"
    "master/2020-02-14_InfraredSolarModules.zip"
)
DATASET_LICENCE = "MIT, Copyright (c) 2020 Raptor Maps, Inc."
METADATA_FILENAME = "module_metadata.json"

# --- Split ------------------------------------------------------------------
# Stratified per class so the rare classes survive the split. Soiling has only
# 205 images; an unstratified split can leave a fold with almost none.

TRAIN_FRACTION = 0.70
VALID_FRACTION = 0.15
SPLIT_SEED = 20260822

# --- Action grouping --------------------------------------------------------
# The 12 published classes collapse into four buckets that each imply a
# DIFFERENT dispatch action. This is the part that ties M5 to the product
# thesis: the environmental bucket is where you do NOT send a technician —
# soiling and vegetation are a cheap clean, not a truck roll with a specialist.
#
# NOT written into dispatch.json. docs/Schema.md is frozen and carries only
# defect_class; adding an action bucket needs D's sign-off and a version bump.
# Recorded here so the mapping exists when that conversation happens.

ACTION_GROUPS = {
    "cell_level_thermal": ["Cell", "Cell-Multi", "Hot-Spot", "Hot-Spot-Multi", "Cracking"],
    "electrical_failure": ["Diode", "Diode-Multi", "Offline-Module"],
    "environmental_reversible": ["Shadowing", "Vegetation", "Soiling"],
    "nominal": ["No-Anomaly"],
}


def download_archive():
    """Fetch the zip once. Skips the download if it is already on disk."""
    os.makedirs(RAW_DIRECTORY, exist_ok=True)
    if os.path.exists(ARCHIVE_PATH):
        print("archive already present, skipping download: {}".format(ARCHIVE_PATH))
        return
    print("downloading {} ...".format(DATASET_URL))
    urllib.request.urlretrieve(DATASET_URL, ARCHIVE_PATH)
    print("saved to {}".format(ARCHIVE_PATH))


def extract_archive():
    """Unzip into data/raw/. Skips if the metadata file is already extracted."""
    if find_metadata_path() is not None:
        print("archive already extracted, skipping")
        return
    print("extracting ...")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        archive.extractall(EXTRACT_DIRECTORY)


def find_metadata_path():
    """Locate module_metadata.json wherever the zip happened to put it."""
    for directory, _subdirectories, filenames in os.walk(EXTRACT_DIRECTORY):
        if METADATA_FILENAME in filenames:
            return os.path.join(directory, METADATA_FILENAME)
    return None


def load_records(metadata_path):
    """Read the metadata into a flat list of (absolute_image_path, class_name).

    The published file is keyed by image number, but this stays tolerant of a
    plain list too rather than failing on a format we have not inspected.
    """
    with open(metadata_path, "r") as handle:
        metadata = json.load(handle)

    entries = metadata.values() if isinstance(metadata, dict) else metadata
    metadata_directory = os.path.dirname(metadata_path)

    records = []
    for entry in entries:
        class_name = entry.get("anomaly_class")
        relative_path = entry.get("image_filepath")
        if not class_name or not relative_path:
            continue
        absolute_path = os.path.join(metadata_directory, relative_path)
        if os.path.exists(absolute_path):
            records.append((absolute_path, class_name))
    return records


def group_by_class(records):
    """Bucket records by class name so the split can be stratified."""
    grouped = {}
    for absolute_path, class_name in records:
        grouped.setdefault(class_name, []).append(absolute_path)
    return grouped


def split_one_class(paths):
    """Shuffle deterministically, then cut into train / valid / test."""
    shuffled = list(paths)
    random.Random(SPLIT_SEED).shuffle(shuffled)
    train_end = int(len(shuffled) * TRAIN_FRACTION)
    valid_end = train_end + int(len(shuffled) * VALID_FRACTION)
    return {
        "train": shuffled[:train_end],
        "valid": shuffled[train_end:valid_end],
        "test": shuffled[valid_end:],
    }


def write_split(grouped):
    """Write folder-per-class, which is the layout yolov8n-cls expects."""
    if os.path.exists(OUTPUT_DIRECTORY):
        shutil.rmtree(OUTPUT_DIRECTORY)

    written = 0
    for class_name, paths in grouped.items():
        for split_name, split_paths in split_one_class(paths).items():
            destination = os.path.join(OUTPUT_DIRECTORY, split_name, class_name)
            os.makedirs(destination, exist_ok=True)
            for source_path in split_paths:
                shutil.copy2(source_path, destination)
                written += 1
    return written


def print_class_table(grouped):
    """Report the class distribution, because it is badly imbalanced."""
    total = sum(len(paths) for paths in grouped.values())
    print("\n{:<22} {:>7}  {:>7}".format("class", "images", "share"))
    print("-" * 40)
    for class_name in sorted(grouped, key=lambda name: -len(grouped[name])):
        count = len(grouped[class_name])
        print("{:<22} {:>7} {:>7.1f}%".format(class_name, count, 100.0 * count / total))
    print("-" * 40)
    print("{:<22} {:>7}".format("TOTAL", total))

    print("\nAction grouping (not a dispatch.json field — see module docstring):")
    for bucket, class_names in ACTION_GROUPS.items():
        bucket_total = sum(len(grouped.get(name, [])) for name in class_names)
        print("  {:<26} {:>7}".format(bucket, bucket_total))

    nominal = len(grouped.get("No-Anomaly", []))
    if total and nominal / total > 0.4:
        print(
            "\nWARNING: No-Anomaly is {:.0f}% of the set. Report PER-CLASS precision"
            "\n         and recall — an overall accuracy figure is inflated by it.".format(
                100.0 * nominal / total
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report, write no splits")
    parser.add_argument("--summary", action="store_true", help="class table only")
    arguments = parser.parse_args()

    print("source:  {}".format(DATASET_URL))
    print("licence: {}".format(DATASET_LICENCE))

    download_archive()
    extract_archive()

    metadata_path = find_metadata_path()
    if metadata_path is None:
        raise SystemExit(
            "could not find {} under {} — inspect the archive layout".format(
                METADATA_FILENAME, EXTRACT_DIRECTORY
            )
        )

    records = load_records(metadata_path)
    if not records:
        raise SystemExit("metadata parsed but no image files resolved on disk")

    grouped = group_by_class(records)
    print_class_table(grouped)

    if arguments.dry_run or arguments.summary:
        print("\ndry run — no splits written")
        return

    written = write_split(grouped)
    print("\nwrote {} images to {}".format(written, OUTPUT_DIRECTORY))
    print("train with: yolo classify train model=yolov8n-cls.pt data={}".format(OUTPUT_DIRECTORY))


if __name__ == "__main__":
    main()
