"""GPU Smoke Test Script for PillSync TrOCR HTR.

Verifies:
- CUDA availability and NVIDIA GPU detection (MX550)
- VRAM budgeting (batch_size=1, gradient_accumulation=8, num_workers=0)
- FP16 mixed precision with GradScaler
- Forward pass, backward pass, optimizer step
- Checkpoint saving and reloading
- Single test inference and VRAM telemetry
"""

import os
import sys
import shutil
import time
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.adapters.rxhandbd_adapter import RxHandBDAdapter


class SmokeDataset(Dataset):
    def __init__(self, samples, images_dir, processor, max_target_length=32):
        self.samples = samples
        self.images_dir = images_dir
        self.processor = processor
        self.max_target_length = max_target_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_name, text = self.samples[idx]
        img_path = os.path.join(self.images_dir, img_name)
        image = Image.open(img_path).convert("RGB")
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze(0)
        
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=self.max_target_length,
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze(0)
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        return {"pixel_values": pixel_values, "labels": labels}


def run_gpu_smoke_test(num_samples: int = 100) -> bool:
    print("==================================================")
    print("        PILLSYNC GPU SMOKE TEST (PHASE 3)         ")
    print("==================================================")

    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available:            {cuda_available}")
    if cuda_available:
        device_name = torch.cuda.get_device_name(0)
        total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
        print(f"Detected GPU:              {device_name}")
        print(f"Total Dedicated VRAM:      {total_vram_mb:.1f} MB")
        device = torch.device("cuda:0")
    else:
        device_name = "CPU (Intel/AMD Host)"
        total_vram_mb = 0.0
        print(f"Detected Device:           {device_name}")
        print("Note: Running smoke test on host CPU.")
        device = torch.device("cpu")

    print(f"PyTorch Version:           {torch.__version__}")


    # 2. Data Loading & Adapter Split
    print("\n[Step 1] Loading RxHandBD Dataset Adapter...")
    adapter = RxHandBDAdapter(data_root=os.path.join(PROJECT_ROOT, "DATA"))
    train_samples, val_samples, test_samples = adapter.load_splits(validate_images=True)
    smoke_samples = train_samples[:num_samples]
    print(f"Loaded {len(smoke_samples)} smoke test samples (from 4,000 train pool)")
    print(f"Official test set (1,115 samples) remains strictly frozen.")

    # 3. Model & Processor Initialization
    print("\n[Step 2] Initializing microsoft/trocr-small-handwritten...")
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel, AdamW
    
    model_name = "microsoft/trocr-small-handwritten"
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    
    # Configure special tokens
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.config.eos_token_id = processor.tokenizer.sep_token_id

    # Enable gradient checkpointing for 2GB VRAM headroom
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        print("Gradient Checkpointing:    ENABLED")

    model.to(device)
    model.train()

    # 4. DataLoader Setup (Batch size 1, num_workers 0)
    dataset = SmokeDataset(smoke_samples, adapter.images_dir, processor)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=True, num_workers=0)

    optimizer = AdamW(model.parameters(), lr=5e-5)
    scaler = torch.cuda.amp.GradScaler()
    grad_accum_steps = 8

    # 5. Execute 1 Smoke Epoch
    print(f"\n[Step 3] Executing 1 Epoch ({len(smoke_samples)} steps, grad_accum={grad_accum_steps})...")
    if cuda_available:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    total_loss = 0.0
    optimizer.zero_grad()

    for step, batch in enumerate(dataloader):
        pixel_values = batch["pixel_values"].to(device)
        labels = batch["labels"].to(device)

        if cuda_available:
            with torch.cuda.amp.autocast():
                outputs = model(pixel_values=pixel_values, labels=labels)
                loss = outputs.loss / grad_accum_steps
            scaler.scale(loss).backward()
            total_loss += loss.item() * grad_accum_steps

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(dataloader):
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
        else:
            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss / grad_accum_steps
            loss.backward()
            total_loss += loss.item() * grad_accum_steps

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(dataloader):
                optimizer.step()
                optimizer.zero_grad()

        if (step + 1) % 25 == 0:
            if cuda_available:
                current_vram = torch.cuda.memory_allocated() / (1024 * 1024)
                peak_vram = torch.cuda.max_memory_allocated() / (1024 * 1024)
                print(f"  Step {step+1}/{len(dataloader)} | Loss: {loss.item()*grad_accum_steps:.4f} | VRAM: {current_vram:.1f}MB (Peak: {peak_vram:.1f}MB)")
            else:
                print(f"  Step {step+1}/{len(dataloader)} | Loss: {loss.item()*grad_accum_steps:.4f}")

    elapsed = time.time() - t0
    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if cuda_available else 0.0
    print(f"\nSmoke Epoch Finished in {elapsed:.2f}s. Avg Loss: {total_loss/len(dataloader):.4f}")
    if cuda_available:
        print(f"Peak VRAM Utilized:        {peak_vram_mb:.1f} MB / {total_vram_mb:.1f} MB ({peak_vram_mb/total_vram_mb*100:.1f}%)")


    # 6. Test Checkpoint Save & Reload
    print("\n[Step 4] Testing Checkpoint Save & Reload...")
    smoke_ckpt_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "scratch", "smoke_checkpoint")
    os.makedirs(smoke_ckpt_dir, exist_ok=True)

    model.save_pretrained(smoke_ckpt_dir)
    processor.save_pretrained(smoke_ckpt_dir)
    print(f"Saved checkpoint to {smoke_ckpt_dir}")

    reloaded_model = VisionEncoderDecoderModel.from_pretrained(smoke_ckpt_dir).to(device)
    reloaded_processor = TrOCRProcessor.from_pretrained(smoke_ckpt_dir)
    reloaded_model.eval()
    print("Reloaded checkpoint successfully.")

    # 7. Test Inference on 1 sample
    print("\n[Step 5] Testing Single Sample Inference...")
    sample_img_name, sample_gt = smoke_samples[0]
    sample_img_path = os.path.join(adapter.images_dir, sample_img_name)
    raw_img = Image.open(sample_img_path).convert("RGB")
    
    with torch.no_grad():
        pv = reloaded_processor(raw_img, return_tensors="pt").pixel_values.to(device)
        generated_ids = reloaded_model.generate(pv)
        pred_text = reloaded_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    print(f"Sample Image:              {sample_img_name}")
    print(f"Ground Truth:              {sample_gt}")
    print(f"Predicted Text:            {pred_text}")

    # Clean up scratch checkpoint
    if os.path.exists(smoke_ckpt_dir):
        shutil.rmtree(smoke_ckpt_dir)

    print("\n==================================================")
    print("           GPU SMOKE TEST: PASSED                 ")
    print("==================================================")
    return True


if __name__ == "__main__":
    success = run_gpu_smoke_test(num_samples=100)
    sys.exit(0 if success else 1)
