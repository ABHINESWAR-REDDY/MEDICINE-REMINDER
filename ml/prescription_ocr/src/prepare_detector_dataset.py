"""Preparation, Split, Deduplication, and Validation for Stage 2 Prescription Detector Dataset.

Creates:
  1. Deterministic 70/15/15 image-level train/val/test splits with zero leakage.
  2. Detector dataset structure in ml/prescription_ocr/data/detector/.
  3. Class mapping: class 1 -> class 0 ('medicine') adhering to standard 0-indexed YOLO format.
  4. Dataset validation checks (image existence, label existence, coordinate validity, leakage).
  5. 20-image ground-truth bounding box visualization artifacts.
"""

import os
import zipfile
import io
import hashlib
import random
import shutil
from typing import Dict, List, Tuple, Set
from PIL import Image, ImageDraw, ImageFont


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute SHA-256 hash for exact duplicate detection."""
    return hashlib.sha256(image_bytes).hexdigest()


def compute_perceptual_hash(img: Image.Image, hash_size: int = 8) -> str:
    """Compute difference perceptual hash (dHash) for near-duplicate detection."""
    # Resize to (hash_size + 1, hash_size) to compute horizontal gradients
    img_gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = list(img_gray.getdata())
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * (hash_size + 1) + col]
            right = pixels[row * (hash_size + 1) + col + 1]
            diff.append("1" if left > right else "0")
    # Also incorporate average intensity to distinguish solid color tones
    avg = sum(pixels) / len(pixels)
    int_flag = "1" if avg > 128 else "0"
    diff.append(int_flag)
    hex_str = f"{int(''.join(diff), 2):017x}"
    return hex_str


def prepare_detector_dataset(
    zip_path: str,
    output_dir: str,
    artifacts_dir: str,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Dict[str, any]:
    random.seed(seed)

    print("=" * 60)
    print("STAGE 2 DETECTOR DATASET PREPARATION & VALIDATION")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(artifacts_dir, exist_ok=True)

    # 1. Inspect and extract metadata from ZIP
    with zipfile.ZipFile(zip_path, "r") as z:
        img_names = sorted([
            n for n in z.namelist()
            if n.lower().endswith((".jpg", ".jpeg", ".png")) and not n.startswith("__MACOSX")
        ])
        lbl_names = sorted([
            n for n in z.namelist()
            if n.lower().endswith(".txt") and "labels/" in n and not n.endswith("classes.txt") and not n.startswith("__MACOSX")
        ])

        print(f"[1/6] Found {len(img_names)} images and {len(lbl_names)} label files in {os.path.basename(zip_path)}.")

        # 2. Extract and hash images to check duplicates
        print("[2/6] Checking for exact duplicates and perceptual near-duplicates...")
        exact_hashes: Dict[str, List[str]] = {}
        perceptual_hashes: Dict[str, List[str]] = {}
        image_data: Dict[str, bytes] = {}
        image_dims: Dict[str, Tuple[int, int]] = {}

        for im_name in img_names:
            b = z.read(im_name)
            image_data[im_name] = b
            im_pil = Image.open(io.BytesIO(b))
            image_dims[im_name] = im_pil.size

            shash = compute_image_hash(b)
            phash = compute_perceptual_hash(im_pil)

            exact_hashes.setdefault(shash, []).append(im_name)
            perceptual_hashes.setdefault(phash, []).append(im_name)

        exact_dupes = {k: v for k, v in exact_hashes.items() if len(v) > 1}
        near_dupes = {k: v for k, v in perceptual_hashes.items() if len(v) > 1 and k not in exact_dupes}

        print(f"      Exact duplicate groups found: {len(exact_dupes)}")
        if exact_dupes:
            for k, v in exact_dupes.items():
                print(f"      - Duplicate group ({len(v)} images): {v}")

        print(f"      Near-duplicate groups found: {len(near_dupes)}")
        if near_dupes:
            for k, v in near_dupes.items():
                print(f"      - Near-duplicate group ({len(v)} images): {v}")

        # Pair images with label files by base ID (e.g., '1.jpeg' -> 'Dataset/labels/1.txt')
        item_pairs = []
        for im_name in img_names:
            base_id = os.path.splitext(os.path.basename(im_name))[0]
            lbl_candidate = f"Dataset/labels/{base_id}.txt"
            if lbl_candidate in lbl_names:
                item_pairs.append((im_name, lbl_candidate, base_id))
            else:
                print(f"      [WARNING] Missing label file for image: {im_name}")

        print(f"      Successfully matched {len(item_pairs)} image-label pairs.")

        # 3. Create Deterministic Split at the Prescription Image Level
        print(f"[3/6] Creating deterministic train/val/test split (seed={seed}, 70/15/15)...")
        shuffled_indices = list(range(len(item_pairs)))
        random.shuffle(shuffled_indices)

        n_total = len(item_pairs)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        n_test = n_total - n_train - n_val

        train_indices = set(shuffled_indices[:n_train])
        val_indices = set(shuffled_indices[n_train:n_train + n_val])
        test_indices = set(shuffled_indices[n_train + n_val:])

        # Guard against duplicate leakage across splits
        for dup_group in list(exact_dupes.values()) + list(near_dupes.values()):
            group_indices = [i for i, (im, _, _) in enumerate(item_pairs) if im in dup_group]
            # If group spans multiple splits, consolidate into train
            split_assignments = set()
            for idx in group_indices:
                if idx in train_indices:
                    split_assignments.add("train")
                elif idx in val_indices:
                    split_assignments.add("val")
                elif idx in test_indices:
                    split_assignments.add("test")
            if len(split_assignments) > 1:
                print(f"      [LEAKAGE PREVENTION] Consolidating duplicate group {dup_group} into 'train'.")
                for idx in group_indices:
                    val_indices.discard(idx)
                    test_indices.discard(idx)
                    train_indices.add(idx)

        splits = {
            "train": [item_pairs[i] for i in sorted(train_indices)],
            "val": [item_pairs[i] for i in sorted(val_indices)],
            "test": [item_pairs[i] for i in sorted(test_indices)],
        }

        print(f"      Train set: {len(splits['train'])} prescriptions")
        print(f"      Val set:   {len(splits['val'])} prescriptions")
        print(f"      Test set:  {len(splits['test'])} prescriptions")

        # 4. Write dataset to disk with class 0 mapping
        print("[4/6] Writing structured detector dataset...")
        total_boxes_written = 0
        boxes_per_split = {"train": 0, "val": 0, "test": 0}

        manifest_dir = os.path.join(output_dir, "manifests")
        os.makedirs(manifest_dir, exist_ok=True)

        for split_name, pairs in splits.items():
            split_img_dir = os.path.join(output_dir, split_name, "images")
            split_lbl_dir = os.path.join(output_dir, split_name, "labels")
            os.makedirs(split_img_dir, exist_ok=True)
            os.makedirs(split_lbl_dir, exist_ok=True)

            manifest_lines = []

            for im_path, lbl_path, base_id in pairs:
                ext = os.path.splitext(im_path)[1].lower()
                out_img_name = f"{base_id}{ext}"
                out_lbl_name = f"{base_id}.txt"

                # Write image
                dest_img_path = os.path.join(split_img_dir, out_img_name)
                with open(dest_img_path, "wb") as f_img:
                    f_img.write(image_data[im_path])

                # Read and normalize label (map class 1 -> class 0)
                raw_lbl = z.read(lbl_path).decode("utf-8").strip()
                converted_lines = []
                for line in raw_lbl.splitlines():
                    if not line.strip():
                        continue
                    parts = line.strip().split()
                    if len(parts) == 5:
                        _, xc, yc, w, h = parts
                        # Map class to 0 ('medicine')
                        converted_lines.append(f"0 {xc} {yc} {w} {h}")
                        boxes_per_split[split_name] += 1
                        total_boxes_written += 1

                dest_lbl_path = os.path.join(split_lbl_dir, out_lbl_name)
                with open(dest_lbl_path, "w", encoding="utf-8") as f_lbl:
                    f_lbl.write("\n".join(converted_lines) + "\n")

                manifest_lines.append(os.path.abspath(dest_img_path))

            # Write manifest file
            with open(os.path.join(manifest_dir, f"{split_name}.txt"), "w", encoding="utf-8") as f_man:
                f_man.write("\n".join(manifest_lines) + "\n")

        # Write dataset.yaml
        yaml_content = f"""# PillSync Prescription Medicine Region Detector Dataset
path: {os.path.abspath(output_dir).replace('\\', '/')}
train: train/images
val: val/images
test: test/images

# Classes
names:
  0: medicine
"""
        yaml_path = os.path.join(output_dir, "dataset.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f_yaml:
            f_yaml.write(yaml_content)

        print(f"      Wrote dataset.yaml to: {yaml_path}")
        print(f"      Bounding boxes written: {total_boxes_written} (Train: {boxes_per_split['train']}, Val: {boxes_per_split['val']}, Test: {boxes_per_split['test']})")

        # 5. Generate 20 Ground Truth Visualizations
        print("[5/6] Generating 20 ground-truth bounding box visualizations...")
        vis_dir = os.path.join(artifacts_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)

        sample_pairs = random.sample(item_pairs, min(20, len(item_pairs)))
        for idx, (im_path, lbl_path, base_id) in enumerate(sample_pairs, 1):
            im_bytes = image_data[im_path]
            img = Image.open(io.BytesIO(im_bytes)).convert("RGB")
            draw = ImageDraw.Draw(img)
            w_img, h_img = img.size

            raw_lbl = z.read(lbl_path).decode("utf-8").strip()
            box_count = 0
            for line in raw_lbl.splitlines():
                if not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) == 5:
                    _, xc, yc, w, h = map(float, parts)
                    x1 = int((xc - w/2) * w_img)
                    y1 = int((yc - h/2) * h_img)
                    x2 = int((xc + w/2) * w_img)
                    y2 = int((yc + h/2) * h_img)

                    # Draw thick rectangle
                    for offset in range(3):
                        draw.rectangle([x1 - offset, y1 - offset, x2 + offset, y2 + offset], outline="red")
                    box_count += 1

            vis_out_path = os.path.join(vis_dir, f"gt_vis_{idx}_rx_{base_id}_boxes_{box_count}.jpg")
            img.save(vis_out_path, quality=90)

        print(f"      Saved 20 visualizations to: {vis_dir}")

        # 6. Comprehensive Dataset Integrity Validation
        print("[6/6] Running full dataset validation suite...")
        validation_errors = []

        for split_name in ["train", "val", "test"]:
            img_dir = os.path.join(output_dir, split_name, "images")
            lbl_dir = os.path.join(output_dir, split_name, "labels")

            imgs_on_disk = sorted(os.listdir(img_dir))
            lbls_on_disk = sorted(os.listdir(lbl_dir))

            if len(imgs_on_disk) != len(lbls_on_disk):
                validation_errors.append(f"Split '{split_name}': Count mismatch ({len(imgs_on_disk)} images vs {len(lbls_on_disk)} labels)")

            for lf in lbls_on_disk:
                lp = os.path.join(lbl_dir, lf)
                with open(lp, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                for line_idx, line in enumerate(content.splitlines()):
                    tokens = line.split()
                    if len(tokens) != 5:
                        validation_errors.append(f"{lp}:{line_idx}: Invalid token count: {len(tokens)}")
                        continue
                    c_id, xc, yc, bw, bh = tokens
                    if c_id != "0":
                        validation_errors.append(f"{lp}:{line_idx}: Invalid class ID '{c_id}', expected '0'")
                    try:
                        xc, yc, bw, bh = float(xc), float(yc), float(bw), float(bh)
                    except ValueError:
                        validation_errors.append(f"{lp}:{line_idx}: Non-float coordinate values")
                        continue
                    if bw <= 0 or bh <= 0:
                        validation_errors.append(f"{lp}:{line_idx}: Zero or negative area box: {line}")
                    if xc < 0 or xc > 1 or yc < 0 or yc > 1 or bw < 0 or bw > 1 or bh < 0 or bh > 1:
                        validation_errors.append(f"{lp}:{line_idx}: Coordinate out of bounds: {line}")

        # Check for cross-split leakage
        train_bases = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(output_dir, "train", "images")))
        val_bases = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(output_dir, "val", "images")))
        test_bases = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(output_dir, "test", "images")))

        leak_train_val = train_bases.intersection(val_bases)
        leak_train_test = train_bases.intersection(test_bases)
        leak_val_test = val_bases.intersection(test_bases)

        if leak_train_val:
            validation_errors.append(f"Leakage detected between train and val: {leak_train_val}")
        if leak_train_test:
            validation_errors.append(f"Leakage detected between train and test: {leak_train_test}")
        if leak_val_test:
            validation_errors.append(f"Leakage detected between val and test: {leak_val_test}")

        print("\n" + "=" * 60)
        if len(validation_errors) == 0:
            print("DATASET READY FOR DETECTOR TRAINING")
        else:
            print(f"DATASET NOT READY ({len(validation_errors)} errors):")
            for err in validation_errors[:10]:
                print(f"  - {err}")
        print("=" * 60 + "\n")

        return {
            "is_ready": len(validation_errors) == 0,
            "errors": validation_errors,
            "total_images": len(img_names),
            "total_boxes": total_boxes_written,
            "splits": {
                "train_images": len(splits["train"]),
                "train_boxes": boxes_per_split["train"],
                "val_images": len(splits["val"]),
                "val_boxes": boxes_per_split["val"],
                "test_images": len(splits["test"]),
                "test_boxes": boxes_per_split["test"],
            },
            "exact_duplicates": len(exact_dupes),
            "near_duplicates": len(near_dupes),
            "yaml_path": yaml_path,
        }


if __name__ == "__main__":
    zip_p = r"backend\data\A Curated Bangladesh-Based Dataset of Handwritten\A Curated Bangladesh-Based Dataset of Handwritten\Dataset.zip"
    out_p = r"ml\prescription_ocr\data\detector"
    art_p = r"ml\prescription_ocr\artifacts\dataset_validation"
    prepare_detector_dataset(zip_p, out_p, art_p)
