import hashlib
import os
import urllib.request

import numpy as np
import onnxruntime as ort
from PIL import Image


MODEL_ID = os.environ.get("WASTE_MODEL", "SriramRokkam/wastewise-garbage-cls")
MODEL_URL = os.environ.get(
    "WASTE_MODEL_URL",
    "https://huggingface.co/SriramRokkam/wastewise-garbage-cls/resolve/main/wastewise-yolo.onnx",
)
MODEL_SHA256 = "2b46d491091dbc0ed98a0f1eaee7fe5739c8fd3eb5bd5935396c3b2712e1f7a6"
MODEL_PATH = "/tmp/wastewise-yolo.onnx"
MIN_CONFIDENCE = float(os.environ.get("WASTE_MIN_CONFIDENCE", "0.65"))

CLASS_NAMES = [
    "battery",
    "biological",
    "cardboard",
    "glass",
    "metal",
    "paper",
    "plastic",
    "trash",
]

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


def _download_model():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    temp_path = MODEL_PATH + ".download"

    try:
        urllib.request.urlretrieve(MODEL_URL, temp_path)
        with open(temp_path, "rb") as model_file:
            digest = hashlib.sha256(model_file.read()).hexdigest()

        if digest != MODEL_SHA256:
            raise RuntimeError("Downloaded AI model failed integrity verification.")

        os.replace(temp_path, MODEL_PATH)
    except Exception as exc:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        raise RuntimeError("Unable to download the AI waste model.") from exc


def _get_model_path():
    if not os.path.exists(MODEL_PATH):
        _download_model()
    return MODEL_PATH


def _get_session():
    model_path = _get_model_path()
    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])


def identify_waste(image_path):
    """Classify an uploaded waste image with the trained WasteWise ONNX model.

    The public model is downloaded lazily to Vercel's writable /tmp directory,
    verified by SHA-256, and then reused for warm invocations. No HF token or
    Hugging Face Inference Provider is required.
    """
    try:
        with Image.open(image_path) as im:
            im.verify()
    except Exception as exc:
        raise ValueError("Invalid or unreadable image") from exc

    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB").resize((224, 224))
            arr = np.asarray(image, dtype=np.float32) / 255.0
            tensor = arr.transpose(2, 0, 1)[np.newaxis, ...]
    except Exception as exc:
        raise ValueError("Unable to prepare the uploaded image for AI classification.") from exc

    try:
        session = _get_session()
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: tensor})
    except Exception as exc:
        raise RuntimeError("The AI waste model could not run on this deployment.") from exc

    if not outputs or len(outputs[0]) == 0:
        raise RuntimeError("The AI model returned no prediction.")

    scores = np.asarray(outputs[0][0], dtype=np.float32).reshape(-1)
    if scores.size != len(CLASS_NAMES):
        raise RuntimeError(
            f"Unexpected AI model output: expected {len(CLASS_NAMES)} classes, got {scores.size}."
        )

    # The model card documents softmax probabilities. If a future model
    # returns logits instead, normalize them so confidence remains meaningful.
    if np.any(scores < 0) or np.any(scores > 1) or not np.isclose(scores.sum(), 1.0, atol=1e-3):
        exp_scores = np.exp(scores - np.max(scores))
        scores = exp_scores / exp_scores.sum()

    class_id = int(np.argmax(scores))
    raw_label = CLASS_NAMES[class_id]
    confidence = float(scores[class_id])

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
