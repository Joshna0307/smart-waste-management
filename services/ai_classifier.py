import numpy as np
from PIL import Image, ImageOps

MODEL_ID = "EcoMind-Custom-Waste-v1"
MIN_CONFIDENCE = float(__import__("os").environ.get("WASTE_MIN_CONFIDENCE", "0.55"))

CLASS_CENTROIDS = np.array([
    [0.416213,0.388344,0.376861,0.190632,0.179537,0.185657,0.395367,0.175825,0.087266,0.096794,0.253845,0.265432,0.322865],
    [0.480337,0.459149,0.427165,0.201454,0.199595,0.196010,0.461838,0.198493,0.085828,0.112663,0.133908,0.055329,0.084157],
    [0.743411,0.650470,0.600640,0.211624,0.245673,0.269615,0.672581,0.231460,0.079053,0.056761,0.226433,0.005791,0.343530],
    [0.437999,0.523402,0.578288,0.242853,0.190815,0.202250,0.504124,0.186356,0.089461,0.080682,0.382864,0.762558,0.109242],
], dtype=np.float32)

CLASS_NAMES = ["pen", "paper_book", "food_waste", "plastic_bottle"]

CLASS_MAP = {
    "pen": {
        "name": "Pen / Plastic Stationery",
        "category": "Plastic",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Collect with accepted plastic/stationery recycling; avoid littering.",
        "environmental_impact": "Plastic stationery can persist in the environment when discarded as mixed waste.",
        "safety": "Do not burn plastic stationery.",
    },
    "paper_book": {
        "name": "Paper / Book",
        "category": "Paper",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Reuse if possible; otherwise keep dry and send to paper recycling.",
        "environmental_impact": "Paper recovery reduces landfill volume and demand for new raw materials.",
        "safety": "Keep paper dry and free from hazardous contamination.",
    },
    "food_waste": {
        "name": "Food / Disposable Waste",
        "category": "Organic",
        "recyclable": False,
        "reusable": False,
        "disposal_method": "Separate food waste for composting/organic collection; separate clean recyclables.",
        "environmental_impact": "Organic waste can generate methane when landfilled.",
        "safety": "Avoid direct contact with contaminated waste.",
    },
    "plastic_bottle": {
        "name": "Plastic Bottle",
        "category": "Plastic",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Empty, rinse, keep dry and send to accepted plastic recycling.",
        "environmental_impact": "Recycling plastic bottles can reduce plastic entering landfill and the environment.",
        "safety": "Do not burn plastic bottles.",
    },
}

def _features(image):
    image = image.convert("RGB").resize((64, 64))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    gx = np.diff(gray, axis=1)
    gy = np.diff(gray, axis=0)
    saturation = (arr.max(axis=2) - arr.min(axis=2)) / (arr.max(axis=2) + 1e-6)

    values = np.array([
        *arr.mean(axis=(0, 1)),
        *arr.std(axis=(0, 1)),
        gray.mean(),
        gray.std(),
        np.mean(np.abs(gx)),
        np.mean(np.abs(gy)),
        saturation.mean(),
        np.mean(arr[:, :, 2] > arr[:, :, 0] * 1.05),
        np.mean(arr[:, :, 0] > arr[:, :, 1] * 1.15),
    ], dtype=np.float32)
    return values

def _predict(features):
    distances = np.linalg.norm(CLASS_CENTROIDS - features, axis=1)
    logits = -8.0 * distances
    logits -= logits.max()
    scores = np.exp(logits)
    scores /= scores.sum()
    return int(np.argmax(scores)), float(scores.max())

def identify_waste(image_path):
    try:
        with Image.open(image_path) as image:
            image.verify()
    except Exception as exc:
        raise ValueError("Invalid or unreadable image") from exc

    try:
        with Image.open(image_path) as image:
            features = _features(image)
    except Exception as exc:
        raise ValueError("Unable to prepare the uploaded image for AI classification.") from exc

    class_id, confidence = _predict(features)
    raw_label = CLASS_NAMES[class_id]
    info = CLASS_MAP[raw_label]

    if confidence < MIN_CONFIDENCE:
        return {
            "name": "Uncertain result",
            "category": "Unknown",
            "confidence": confidence,
            "recyclable": False,
            "reusable": False,
            "disposal_method": "Please upload a clearer image containing one main waste item.",
            "environmental_impact": "The custom model confidence is below the configured threshold.",
            "safety": "Do not rely on this result for hazardous-waste disposal.",
            "is_demo": False,
            "uncertain": True,
            "model": MODEL_ID,
        }

    return {
        "name": info["name"],
        "category": info["category"],
        "confidence": confidence,
        "recyclable": info["recyclable"],
        "reusable": info["reusable"],
        "disposal_method": info["disposal_method"],
        "environmental_impact": info["environmental_impact"],
        "safety": info["safety"],
        "is_demo": False,
        "uncertain": False,
        "model": MODEL_ID,
    }
