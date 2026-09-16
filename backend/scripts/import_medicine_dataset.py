"""Dataset Ingestion Script for Phase 3 OCR Medicine Reference Layer.

Reads medicine_dataset_enhanced.csv, normalizes fields, strips empty columns,
deduplicates distinct reference combinations, and populates the medicine_references table.
"""

import os
import csv
import re
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.medicine_reference import MedicineReference
from app.core.logging import logger


def normalize_medicine_name(name: str) -> str:
    """Normalize medicine name for robust matching (lowercase, alphanumeric only)."""
    if not name:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def clean_string(val: str) -> str:
    """Clean and strip string values."""
    if not val:
        return ""
    val = val.strip()
    if val.lower() in ("nan", "null", "none", "n/a", "unnamed: 7"):
        return ""
    return val


def import_medicine_dataset(csv_path: str = None) -> dict:
    """
    Ingest medicine dataset into medicine_references table.
    
    Args:
        csv_path: Path to medicine_dataset_enhanced.csv. If None, uses backend/data/ default.
        
    Returns:
        Summary metrics dictionary.
    """
    if not csv_path:
        csv_path = os.path.join(str(backend_dir), "data", "medicine_dataset_enhanced.csv")

    if not os.path.exists(csv_path):
        # Fallback to Downloads if not in data/
        alt_path = os.path.expanduser(r"C:\Users\admin\Downloads\medicine_dataset_enhanced.csv")
        if os.path.exists(alt_path):
            csv_path = alt_path
        else:
            raise FileNotFoundError(f"Medicine dataset not found at {csv_path}")

    logger.info("Starting ingestion from: %s", csv_path)

    db: Session = SessionLocal()
    try:
        # Check if records already exist
        existing_count = db.query(MedicineReference).count()
        if existing_count > 0:
            logger.info("Found %d existing medicine_reference records. Resetting reference table...", existing_count)
            db.query(MedicineReference).delete()
            db.commit()

        seen_combinations = set()
        unique_names = set()
        records_to_insert = []
        total_rows = 0
        ignored_empty_columns = ["Unnamed: 7", "Remainder_Time"]

        with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            
            for row in reader:
                total_rows += 1
                name = clean_string(row.get("Name", ""))
                if not name:
                    continue

                category = clean_string(row.get("Category", ""))
                dosage_form = clean_string(row.get("Dosage Form", ""))
                strength = clean_string(row.get("Strength", ""))
                manufacturer = clean_string(row.get("Manufacturer", ""))
                indication = clean_string(row.get("Indication", ""))
                classification = clean_string(row.get("Classification", ""))
                frequency = clean_string(row.get("Frequency", ""))

                normalized_name = normalize_medicine_name(name)
                unique_names.add(name)

                # Composite key to prevent exact duplicate reference rows
                combo_key = (
                    name,
                    normalized_name,
                    category,
                    dosage_form,
                    strength,
                    manufacturer,
                    indication,
                    classification,
                    frequency,
                )

                if combo_key in seen_combinations:
                    continue

                seen_combinations.add(combo_key)
                records_to_insert.append(
                    MedicineReference(
                        name=name,
                        normalized_name=normalized_name,
                        category=category or None,
                        dosage_form=dosage_form or None,
                        strength=strength or None,
                        manufacturer=manufacturer or None,
                        indication=indication or None,
                        classification=classification or None,
                        frequency=frequency or None,
                    )
                )

        logger.info(
            "Parsed %d rows from CSV. Found %d unique medicine names and %d distinct reference specifications.",
            total_rows,
            len(unique_names),
            len(records_to_insert),
        )

        # Batch insert for high performance
        BATCH_SIZE = 5000
        for i in range(0, len(records_to_insert), BATCH_SIZE):
            batch = records_to_insert[i : i + BATCH_SIZE]
            db.bulk_save_objects(batch)
            db.commit()

        final_count = db.query(MedicineReference).count()
        logger.info("Successfully ingested %d reference records into medicine_references table.", final_count)

        return {
            "total_csv_rows": total_rows,
            "unique_medicine_names": len(unique_names),
            "distinct_records_imported": final_count,
            "ignored_empty_columns": ignored_empty_columns,
            "status": "SUCCESS",
        }
    except Exception as e:
        db.rollback()
        logger.error("Dataset ingestion failed: %s", str(e), exc_info=True)
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    result = import_medicine_dataset()
    print("Ingestion Result:", result)
