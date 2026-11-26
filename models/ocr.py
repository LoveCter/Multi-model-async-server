"""TrOCR: reads images that contain ONE line of printed text."""
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

MODEL_NAME = "microsoft/trocr-small-printed"


def load(device: str):
    processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()
    return {"processor": processor, "model": model}


def predict(bundle, pil_image, device: str, question: str = None) -> dict:
    pixel_values = bundle["processor"](pil_image, return_tensors="pt").pixel_values.to(device)
    with torch.no_grad():
        ids = bundle["model"].generate(pixel_values)
    text = bundle["processor"].batch_decode(ids, skip_special_tokens=True)[0]
    return {"text": text}
