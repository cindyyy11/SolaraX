from ultralytics import YOLO

# Load the trained model once
model = YOLO("model/best.pt")

CONFIDENCE_THRESHOLD = 0.65

def classify_defect(image_path):
    """
    Classify a thermal solar-panel image.

    Input:
        image_path:
            Path to a thermal image.

    Output:
        Dictionary containing:
        - predicted defect class
        - confidence score
    """

    # Give the image to our trained YOLO model
    results = model(image_path)

    # We only gave YOLO one image,
    # so take the first result.
    result = results[0]

    # Get the model's highest-probability class.
    class_id = result.probs.top1

    # Convert class number into class name.
    class_name = result.names[class_id]

    # Get confidence score.
    confidence = float(result.probs.top1conf)

    # Reject predictions the model is not confident enough about.
    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "class": "Unknown",
            "confidence": confidence,
        }
    # Return structured information.
    return {
        "class": class_name,
        "confidence": confidence,
    }