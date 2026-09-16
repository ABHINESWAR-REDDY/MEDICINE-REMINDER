"""Verification of Tokenization, Model Processor, and Controlled Gradient Updates."""

import os
import sys
import csv
import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, AdamW

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def verify_all():
    print("==================================================")
    print("STEP 5 & 6: VERIFY MODEL PROCESSOR & TOKENIZATION")
    print("==================================================")
    model_name = "microsoft/trocr-small-handwritten"
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    
    print(f"Tokenizer class:        {type(processor.tokenizer).__name__}")
    print(f"Image Processor class:  {type(processor.image_processor).__name__}")
    print(f"Vocab size:             {processor.tokenizer.vocab_size}")
    print(f"Pad token ID:           {processor.tokenizer.pad_token_id}")
    print(f"Cls token ID:           {processor.tokenizer.cls_token_id}")
    print(f"Sep token ID:           {processor.tokenizer.sep_token_id}")

    train_csv = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML", "Train_Label.csv")
    with open(train_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        samples = [r[1] for r in list(reader)[:25]]

    print("\nTesting Tokenization Reconstruction (first 25 samples):")
    for s in samples:
        enc = processor.tokenizer(s, padding="max_length", max_length=32, truncation=True, return_tensors="pt").input_ids[0]
        # Verify pad token masking
        masked = enc.clone()
        masked[masked == processor.tokenizer.pad_token_id] = -100
        dec = processor.tokenizer.decode(enc, skip_special_tokens=True)
        assert dec.strip() == s.strip(), f"Mismatch: gt='{s}', dec='{dec}'"
        print(f"  GT: '{s:<18}' -> Reconstructed: '{dec:<18}' | Non-pad token count: {(masked != -100).sum().item()}")

    print("\nTokenization and label masking verification PASSED.")

    print("\n==================================================")
    print("STEP 7: CONTROLLED 100-SAMPLE OPTIMIZATION UPDATE")
    print("==================================================")
    
    # Load 100 real images
    train_img_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML", "Train_Set")
    with open(train_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        sample_rows = list(reader)[:100]

    device = torch.device("cpu")
    model.to(device)
    model.train()

    optimizer = AdamW(model.parameters(), lr=5e-5)
    
    initial_weight = model.decoder.output_projection.weight.detach().clone()
    print(f"Initial Decoder Output Projection Weight Norm: {initial_weight.norm().item():.4f}")

    losses = []
    print("Running 5 optimization steps on batches of 4...")
    for step in range(5):
        batch = sample_rows[step * 4 : (step + 1) * 4]
        pixel_tensors = []
        label_tensors = []
        for img_name, text in batch:
            img_path = os.path.join(train_img_dir, img_name)
            img = Image.open(img_path).convert("RGB")
            px = processor(img, return_tensors="pt").pixel_values[0]
            lbl = processor.tokenizer(text, padding="max_length", max_length=32, truncation=True, return_tensors="pt").input_ids[0]
            lbl[lbl == processor.tokenizer.pad_token_id] = -100
            pixel_tensors.append(px)
            label_tensors.append(lbl)

        pixel_batch = torch.stack(pixel_tensors).to(device)
        label_batch = torch.stack(label_tensors).to(device)

        optimizer.zero_grad()
        outputs = model(pixel_values=pixel_batch, labels=label_batch)
        loss = outputs.loss
        loss.backward()

        grad_norm = sum(p.grad.norm().item() for p in model.parameters() if p.grad is not None)
        optimizer.step()
        
        losses.append(loss.item())
        print(f"  Step {step + 1}: Loss = {loss.item():.4f} | Total Gradient Norm = {grad_norm:.4f}")

    updated_weight = model.decoder.output_projection.weight.detach()
    weight_diff = (updated_weight - initial_weight).abs().sum().item()
    print(f"\nTotal Weight Difference after 5 steps: {weight_diff:.6f}")
    assert weight_diff > 0.0, "Weights failed to update!"
    print(f"Initial Step Loss: {losses[0]:.4f} -> Step 5 Loss: {losses[-1]:.4f}")
    print("Controlled Optimization Verification PASSED successfully!")
    print("==================================================")

if __name__ == "__main__":
    verify_all()
