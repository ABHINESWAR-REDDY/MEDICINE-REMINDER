"""Test base pretrained TrOCR model on RxHandBD test crops.
"""

import os
import csv
import torch
import rapidfuzz.distance.Levenshtein as lev
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
test_csv = os.path.join(PROJECT_ROOT, "DATA", "Test_Label.csv")
test_dir = os.path.join(PROJECT_ROOT, "DATA", "Test_Set")

print("Loading base pretrained model: microsoft/trocr-small-handwritten...")
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-small-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-handwritten")
model.eval()

valid_samples = []
with open(test_csv, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames or []
    img_col = "filename" if "filename" in fieldnames else fieldnames[0]
    label_col = "text" if "text" in fieldnames else ("label" if "label" in fieldnames else fieldnames[1])
    for row in reader:
        img_name = str(row.get(img_col, "")).strip()
        lbl = str(row.get(label_col, "")).strip()
        img_p = os.path.join(test_dir, img_name)
        if os.path.exists(img_p) and lbl:
            valid_samples.append((img_p, lbl, img_name))

print(f"Testing on 20 samples from {len(valid_samples)} test samples...")
cers = []
for img_path, gt, fname in valid_samples[:20]:
    img = Image.open(img_path).convert("RGB")
    pixel_values = processor(img, return_tensors="pt").pixel_values
    with torch.no_grad():
        generated_ids = model.generate(pixel_values, max_new_tokens=30)
    pred = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    c_dist = lev.distance(pred.lower(), gt.lower())
    cer = c_dist / max(len(gt), 1)
    cers.append(cer)
    print(f"File: {fname:10s} | GT: '{gt:15s}' | Pred: '{pred:15s}' | CER: {cer:.2f}")

print(f"\nMean CER on 20 samples with pretrained base TrOCR: {sum(cers)/len(cers):.4f}")
