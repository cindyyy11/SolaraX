from defect_classifier import classify_defect


image_path = "data/raw/defects/test/Hot-Spot/6739.jpg"

result = classify_defect(image_path)

print("Prediction:", result["class"])
print(
    "Confidence:",
    round(result["confidence"] * 100, 2),
    "%"
)