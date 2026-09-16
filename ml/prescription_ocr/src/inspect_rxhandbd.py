"""Inspect and verify RxHandBD-ML dataset structure, label mapping, and image integrity."""

import os
import csv
import json
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def inspect():
    data_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML")
    train_img_dir = os.path.join(data_dir, "Train_Set")
    test_img_dir = os.path.join(data_dir, "Test_Set")
    train_csv = os.path.join(data_dir, "Train_Label.csv")
    test_csv = os.path.join(data_dir, "Test_Label.csv")

    def load_csv(path):
        rows = []
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            for r in reader:
                if len(r) >= 2:
                    rows.append((r[0].strip(), r[1].strip()))
        return header, rows

    train_header, train_rows = load_csv(train_csv)
    test_header, test_rows = load_csv(test_csv)

    print("=" * 70)
    print("RxHandBD-ML DATASET INSPECTION")
    print("=" * 70)
    print(f"Train CSV path:       {train_csv}")
    print(f"Test CSV path:        {test_csv}")
    print(f"Train Header:         {train_header}")
    print(f"Test Header:          {test_header}")
    print(f"Train CSV Rows:       {len(train_rows)}")
    print(f"Test CSV Rows:        {len(test_rows)}")

    train_files = set(os.listdir(train_img_dir))
    test_files = set(os.listdir(test_img_dir))

    def resolve_filename(fname, file_set):
        if fname in file_set:
            return fname
        for ext in [".jpg", ".jpeg", ".png"]:
            if fname + ext in file_set:
                return fname + ext
        return None

    train_matched = []
    for r in train_rows:
        res = resolve_filename(r[0], train_files)
        if res:
            train_matched.append((res, r[1]))

    test_matched = []
    for r in test_rows:
        res = resolve_filename(r[0], test_files)
        if res:
            test_matched.append((res, r[1]))

    print(f"\nTrain Images in Dir:  {len(train_files)}")
    print(f"Train Matched Pairs:  {len(train_matched)}")
    print(f"Missing Train Images: {len(train_rows) - len(train_matched)}")

    print(f"\nTest Images in Dir:   {len(test_files)}")
    print(f"Test Matched Pairs:   {len(test_matched)}")
    print(f"Missing Test Images:  {len(test_rows) - len(test_matched)}")

    # Check for empty labels
    empty_train = [r for r in train_rows if not r[1]]
    empty_test = [r for r in test_rows if not r[1]]
    print(f"\nEmpty Train Labels:   {len(empty_train)}")
    print(f"Empty Test Labels:    {len(empty_test)}")

    # Check for duplicate image names
    train_names = [r[0] for r in train_rows]
    test_names = [r[0] for r in test_rows]
    dup_train = len(train_names) - len(set(train_names))
    dup_test = len(test_names) - len(set(test_names))
    print(f"Duplicate Train Keys: {dup_train}")
    print(f"Duplicate Test Keys:  {dup_test}")

    # Check label length and character distribution
    all_train_texts = [r[1] for r in train_matched]
    all_test_texts = [r[1] for r in test_matched]

    char_set = set("".join(all_train_texts))
    print(f"\nUnique Characters in Train: {len(char_set)}")
    print(f"Sample Characters:          {sorted(list(char_set))[:30]}")

    print("\nSample 5 Training Pairs:")
    for r in train_matched[:5]:
        print(f"  {r[0]} -> \"{r[1]}\"")

    print("\nSample 5 Testing Pairs:")
    for r in test_matched[:5]:
        print(f"  {r[0]} -> \"{r[1]}\"")

    print("=" * 70)


if __name__ == "__main__":
    inspect()
