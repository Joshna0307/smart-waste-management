import os
from PIL import Image
from huggingface_hub import InferenceClient

MODEL_ID = os.environ.get("WASTE_MODEL", "SriramRokkam/wastewise-garbage-cls")
MIN_CONFIDENCE = float(os.environ.get("WASTE_MIN_CONFIDENCE", "0.55"))

CLASS_MAP = {
    "battery": {
        "name": "Battery",
        "category": "Hazardous",
        "recyclable": True,
        "reusable": False,
        "disposal_method": "Use an authorized battery/e-waste collection point",
        "environmental_impact": "Batteries can release hazardous materials if disposed of incorrectly.",
        "safety": "Do not puncture, burn or place in household waste.",
    },
    "biological": {
        "name": "Biological Waste",
        "category": "Organic",
        "recyclable": False,
        "reusable": True,
        "disposal_method": "Compost or use an organic-waste bin",
        "environmental_impact": "Organic waste can generate methane when landfilled.",
        "safety": "Avoid handling contaminated biological material directly.",
    },
    "cardboard": {
        "name": "Cardboard",
        "category": "Paper",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Keep dry and send to paper/cardboard recycling",
        "environmental_impact": "Recovering cardboard reduces landfill volume and raw-material demand.",
        "safety": "Flatten boxes and remove food contamination where possible.",
    },
    "glass": {
        "name": "Glass",
        "category": "Glass",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Use a glass recycling collection point",
        "environmental_impact": "Glass can be recycled repeatedly when properly collected.",
        "safety": "Handle broken glass carefully.",
    },
    "metal": {
        "name": "Metal",
        "category": "Metal",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Rinse and send accepted metal to recycling",
        "environmental_impact": "Metal recovery can reduce demand for new raw materials.",
        "safety": "Watch for sharp edges.",
    },
    "paper": {
        "name": "Paper",
        "category": "Paper",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Keep dry and recycle with accepted paper",
        "environmental_impact": "Paper recovery reduces landfill volume and raw-material demand.",
        "safety": "Keep paper dry and free from hazardous contamination.",
    },
    "plastic": {
        "name": "Plastic",
        "category": "Plastic",
        "recyclable": True,
        "reusable": True,
        "disposal_method": "Clean, dry and send accepted plastic to recycling",
        "environmental_impact": "Plastic can persist for a long time when littered or landfilled.",
        "safety": "Do not burn plastic.",
    },
    "trash": {
        "name": "General Waste",
        "category": "General",
        "recyclable": False,
        "reusable": False,
        "disposal_method": "Use the appropriate municipal general-waste channel",
        "environmental_impact": "Mixed waste is harder to recover and can increase landfill use.",
        "safety": "Do not handle unknown hazardous materials directly.",
    },
}

def identify_waste(image_path):
    """Classify the uploaded image using a trained waste image model.

    The model is served through Hugging Face Inference Providers so the Flask
    deployment does not need to package a large ML model inside the Vercel
    function. A HF_TOKEN environment variable is required.
    """
    try:
        with Image.open(image_path) as im:
            im.verify()
    except Exception as exc:
        raise ValueError("Invalid or unreadable image") from exc

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("AI classifier is not configured. Add HF_TOKEN to the deployment environment.")

    client = InferenceClient(provider="auto", api_key=token)

    with open(image_path, "rb") as image_file:
        predictions = client.image_classification(
            image_file.read(),
            model=MODEL_ID,
        )

    if not predictions:
        raise RuntimeError("The AI model returned no prediction.")

    top = max(predictions, key=lambda item: float(item.score))
    raw_label = str(top.label).strip().lower()
    confidence = float(top.score)

    info = CLASS_MAP.get(raw_label)
    if info is None:
        raise RuntimeError(f"Unsupported model class returned: {raw_label}")

    if confidence < MIN_CONFIDENCE:
        return {
            "name": "Uncertain result",
            "category": "Unknown",
            "confidence": confidence,
            "recyclable": False,
            "reusable": False,
            "disposal_method": "Please upload a clearer, single-waste image",
            "environmental_impact": "The model confidence is below the safety threshold.",
            "safety": "Do not rely on this result for hazardous-waste disposal.",
            "is_demo": False,
            "uncertain": True,
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
