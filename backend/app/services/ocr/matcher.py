"""Medicine Reference Matching and Confidence Scoring Module.

Matches OCR-extracted medicine candidates against the normalized medicine_references
knowledge base using exact, normalized, and fuzzy token similarity.
"""

import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from rapidfuzz import fuzz

from app.models.medicine_reference import MedicineReference
from app.core.logging import logger


class MedicineMatcher:
    """Matches text tokens against the global MedicineReference knowledge base."""

    CONFIDENCE_HIGH = 0.90
    CONFIDENCE_MEDIUM = 0.75

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._reference_cache: Optional[List[Dict[str, Any]]] = None

    def _normalize(self, text: str) -> str:
        """Strip non-alphanumeric characters and lowercase."""
        if not text:
            return ""
        return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

    def _load_reference_cache(self) -> List[Dict[str, Any]]:
        """Load unique reference medicines from database into an in-memory matching index."""
        if self._reference_cache is not None:
            return self._reference_cache

        # 1. Load from DB if available
        references = []
        if self.db:
            try:
                db_refs = self.db.query(MedicineReference).all()
                references.extend(db_refs)
            except Exception as e:
                logger.warning("Could not query MedicineReference table: %s", str(e))

        # 2. Always index full reference databases (medicine_dataset_enhanced.csv + all_medicine databased.csv)
        import os
        import csv
        
        med_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "DATA", "medicine names"))
        data_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "DATA"))
        
        # Load enhanced medicine dataset (medicine_dataset_enhanced.csv - 50,000 items)
        csv_path = os.path.join(med_dir, "medicine_dataset_enhanced.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("Name", "").strip()
                        if name:
                            references.append(type("MedicineRefDummy", (), {
                                "name": name,
                                "normalized_name": self._normalize(name),
                                "category": row.get("Category"),
                                "dosage_form": row.get("Dosage Form"),
                                "strength": row.get("Strength"),
                                "manufacturer": row.get("Manufacturer"),
                                "indication": row.get("Indication"),
                                "frequency": row.get("Frequency"),
                            })())
            except Exception as e:
                logger.warning("Could not load reference CSV: %s", str(e))

        # Load pharmaceutical database (all_medicine databased.csv)
        all_med_path = os.path.join(med_dir, "all_medicine databased.csv")
        if os.path.exists(all_med_path):
            try:
                with open(all_med_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        raw_name = row.get("name", "").strip()
                        if raw_name:
                            form_match = re.search(r"\b(tablet|capsule|syrup|drop|drops|injection|cream|gel|ointment|inhaler)s?\b", raw_name, re.I)
                            d_form = form_match.group(0).upper() if form_match else None
                            str_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|iu|%))\b", raw_name, re.I)
                            d_str = str_match.group(0) if str_match else None

                            references.append(type("MedicineRefDummy", (), {
                                "name": raw_name.title(),
                                "normalized_name": self._normalize(raw_name),
                                "category": row.get("Therapeutic Class"),
                                "dosage_form": d_form,
                                "strength": d_str,
                                "manufacturer": None,
                                "indication": row.get("use0"),
                                "frequency": None,
                            })())

                            base_brand = re.split(r"\s+\d+", raw_name)[0].strip()
                            if len(base_brand) >= 3 and self._normalize(base_brand) != self._normalize(raw_name):
                                references.append(type("MedicineRefDummy", (), {
                                    "name": base_brand.title(),
                                    "normalized_name": self._normalize(base_brand),
                                    "category": row.get("Therapeutic Class"),
                                    "dosage_form": d_form,
                                    "strength": d_str,
                                    "manufacturer": None,
                                    "indication": row.get("use0"),
                                    "frequency": None,
                                })())
            except Exception as e:
                logger.warning("Could not load all_medicine databased.csv: %s", str(e))

        # Also load common brand dictionary from RxHandBD / Doctor BD datasets
        for lbl_file in ["Train_Label.csv", "Test_Label.csv"]:
            lbl_path = os.path.join(data_root, lbl_file)
            if os.path.exists(lbl_path):
                try:
                    with open(lbl_path, "r", encoding="utf-8", errors="ignore") as f:
                        reader = csv.reader(f)
                        next(reader, None)
                        for r in reader:
                            if len(r) >= 2 and r[1].strip():
                                b_text = r[1].strip()
                                b_name = re.split(r"\s+\d+", b_text)[0].strip()
                                if len(b_name) >= 3:
                                    references.append(type("MedicineRefDummy", (), {
                                        "name": b_name.title(),
                                        "normalized_name": self._normalize(b_name),
                                        "category": "Prescription Medicine",
                                        "dosage_form": "TABLET",
                                        "strength": None,
                                        "manufacturer": None,
                                        "indication": None,
                                        "frequency": None,
                                    })())
                except Exception:
                    pass

        grouped: Dict[str, Dict[str, Any]] = {}


        for ref in references:
            name = ref.name
            if name not in grouped:
                grouped[name] = {
                    "name": name,
                    "normalized_name": ref.normalized_name or self._normalize(name),
                    "categories": set(),
                    "dosage_forms": set(),
                    "strengths": set(),
                    "manufacturers": set(),
                    "indications": set(),
                    "frequencies": set(),
                }
            if ref.category:
                grouped[name]["categories"].add(ref.category)
            if ref.dosage_form:
                grouped[name]["dosage_forms"].add(ref.dosage_form)
            if ref.strength:
                grouped[name]["strengths"].add(ref.strength)
            if ref.manufacturer:
                grouped[name]["manufacturers"].add(ref.manufacturer)
            if ref.indication:
                grouped[name]["indications"].add(ref.indication)
            if ref.frequency:
                grouped[name]["frequencies"].add(ref.frequency)

        self._reference_cache = [
            {
                "name": data["name"],
                "normalized_name": data["normalized_name"],
                "category": next(iter(data["categories"]), None),
                "dosage_form": next(iter(data["dosage_forms"]), None),
                "strength": next(iter(data["strengths"]), None),
                "categories": sorted(list(data["categories"])),
                "dosage_forms": sorted(list(data["dosage_forms"])),
                "strengths": sorted(list(data["strengths"])),
            }
            for data in grouped.values()
        ]

        self._exact_map = {item["name"].lower(): item for item in self._reference_cache}
        self._norm_map = {item["normalized_name"]: item for item in self._reference_cache}
        
        # Build compact unique brand root set for sub-millisecond C++ SIMD fuzzy matching
        unique_brands = set()
        self._brand_to_items: Dict[str, List[Dict[str, Any]]] = {}
        for item in self._reference_cache:
            name_parts = item["name"].split()
            if name_parts:
                brand_root = name_parts[0].lower()
                if len(brand_root) >= 3:
                    unique_brands.add(brand_root)
                    if brand_root not in self._brand_to_items:
                        self._brand_to_items[brand_root] = []
                    self._brand_to_items[brand_root].append(item)
                # Also add full name if short
                if len(item["name"]) <= 20:
                    unique_brands.add(item["name"].lower())
                    if item["name"].lower() not in self._brand_to_items:
                        self._brand_to_items[item["name"].lower()] = []
                    self._brand_to_items[item["name"].lower()].append(item)

        self._searchable_brands = sorted(list(unique_brands))
        return self._reference_cache

    def get_confidence_level(self, score: float) -> str:
        """Categorize numerical confidence score into engineering threshold levels."""
        if score >= self.CONFIDENCE_HIGH:
            return "HIGH"
        elif score >= self.CONFIDENCE_MEDIUM:
            return "MEDIUM"
        else:
            return "LOW"

    def match_medicine_name(self, candidate_name: str) -> Dict[str, Any]:
        """
        Match a candidate name string against the reference dataset with C++ accelerated search.
        
        Returns:
            Dict containing best match, confidence score, confidence level,
            match type, is_ambiguous flag, auto_select_eligible, and top candidates.
        """
        if not candidate_name or not candidate_name.strip():
            return {
                "matched_name": None,
                "confidence": 0.0,
                "confidence_level": "LOW",
                "match_type": "NONE",
                "is_ambiguous": False,
                "auto_select_eligible": False,
                "requires_user_review": True,
                "reference_data": None,
                "candidates": [],
            }

        cleaned_candidate = candidate_name.strip()
        norm_candidate = self._normalize(cleaned_candidate)
        cache = self._load_reference_cache()

        if not cache:
            return {
                "matched_name": cleaned_candidate,
                "confidence": 0.0,
                "confidence_level": "LOW",
                "match_type": "NO_DATABASE_RECORDS",
                "is_ambiguous": False,
                "auto_select_eligible": False,
                "requires_user_review": True,
                "reference_data": None,
                "candidates": [],
            }

        # 1. Instant Exact match (O(1))
        exact_item = getattr(self, "_exact_map", {}).get(cleaned_candidate.lower())
        if exact_item:
            return {
                "matched_name": exact_item["name"],
                "confidence": 1.0,
                "confidence_level": "HIGH",
                "match_type": "EXACT",
                "is_ambiguous": False,
                "auto_select_eligible": True,
                "requires_user_review": True,
                "reference_data": exact_item,
                "candidates": [{"dataset_name": exact_item["name"], "confidence": 1.0, "match_type": "EXACT"}],
            }

        # 2. Instant Normalized match (O(1))
        norm_item = getattr(self, "_norm_map", {}).get(norm_candidate)
        if norm_item:
            return {
                "matched_name": norm_item["name"],
                "confidence": 1.0,
                "confidence_level": "HIGH",
                "match_type": "NORMALIZED",
                "is_ambiguous": False,
                "auto_select_eligible": True,
                "requires_user_review": True,
                "reference_data": norm_item,
                "candidates": [{"dataset_name": norm_item["name"], "confidence": 1.0, "match_type": "NORMALIZED"}],
            }

        # 3. High-Speed Fuzzy Matching via rapidfuzz.process.extract on unique brand roots
        scored_candidates = []
        try:
            import rapidfuzz.process
            results = rapidfuzz.process.extract(
                cleaned_candidate.lower(),
                getattr(self, "_searchable_brands", []),
                scorer=fuzz.ratio,
                limit=5,
                score_cutoff=50.0,
            )
            for match_str, score, _ in results:
                matched_items = self._brand_to_items.get(match_str, [])
                if matched_items:
                    best_item = matched_items[0]
                    scored_candidates.append({
                        "dataset_name": best_item["name"],
                        "confidence": round(score / 100.0, 2),
                        "match_type": "FUZZY",
                        "reference_data": best_item,
                    })
        except Exception:
            pass



        scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)

        if scored_candidates:
            best = scored_candidates[0]
            confidence = best["confidence"]
            level = self.get_confidence_level(confidence)

            # Ambiguity check: if top 2 candidates are within 0.08 of each other
            is_ambiguous = False
            if len(scored_candidates) > 1 and (best["confidence"] - scored_candidates[1]["confidence"]) < 0.08:
                is_ambiguous = True

            # Automatic selection is only safe for non-ambiguous HIGH confidence matches (>= 0.90)
            auto_select_eligible = (level == "HIGH" and not is_ambiguous and confidence >= 0.90)

            # For LOW confidence (< 0.75), do not populate matched_name to prevent false replacement
            safe_matched_name = best["dataset_name"] if confidence >= self.CONFIDENCE_MEDIUM else None

            return {
                "matched_name": safe_matched_name,
                "confidence": confidence,
                "confidence_level": level,
                "match_type": "FUZZY",
                "is_ambiguous": is_ambiguous,
                "auto_select_eligible": auto_select_eligible,
                "requires_user_review": True,
                "reference_data": best["reference_data"] if safe_matched_name else None,
                "candidates": [
                    {"dataset_name": c["dataset_name"], "confidence": c["confidence"], "match_type": c["match_type"]}
                    for c in scored_candidates[:5]
                ],
            }

        # No candidate found above threshold
        return {
            "matched_name": None,
            "confidence": 0.0,
            "confidence_level": "LOW",
            "match_type": "NONE",
            "is_ambiguous": False,
            "auto_select_eligible": False,
            "requires_user_review": True,
            "reference_data": None,
            "candidates": [],
        }

    def find_best_match(self, candidate_name: str) -> Dict[str, Any]:
        """Alias for match_medicine_name for consistent service integration."""
        return self.match_medicine_name(candidate_name)
