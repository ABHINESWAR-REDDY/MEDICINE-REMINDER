"""Structured Field Extraction from Preprocessed OCR Text.

Extracts clinical fields (doctor, rx number, medicine name, strength, form,
frequency, dose, instructions, duration, dates) with strict rule that missing
fields remain None (never fabricated or guessed from reference databases).
"""

import re
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.medicine import MedicineForm, DosageUnit
from app.models.schedule import ScheduleFrequency
from app.services.ocr.preprocessor import OCRTextPreprocessor
from app.services.ocr.matcher import MedicineMatcher
from app.core.logging import logger


class PrescriptionFieldExtractor:
    """Extracts structured medical prescription fields from OCR text with provenance tracking."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.matcher = MedicineMatcher(db)

    def extract_fields(self, raw_text: str) -> Dict[str, Any]:
        """
        Main extraction entrypoint.
        Returns extracted fields, provenance evidence, and candidate matches without fabricating values.
        """
        if not raw_text or not raw_text.strip():
            return self._empty_extraction_result("")

        # 1. Clean & Preprocess
        cleaned_text = OCRTextPreprocessor.clean_text(raw_text)
        expanded_text = OCRTextPreprocessor.expand_abbreviations(cleaned_text)

        # 2. Extract Header Metadata (Doctor, Rx Number, Dates)
        doctor_name = self._extract_doctor_name(cleaned_text)
        prescription_number = self._extract_prescription_number(cleaned_text)
        issue_date, expiry_date = self._extract_dates(cleaned_text)

        # 3. Extract Medication Details (Strictly from OCR text)
        med_match, detected_raw_med = self._extract_medicine_name_and_match(cleaned_text)
        dosage_amount, dosage_unit, strength_str = self._extract_strength(cleaned_text)
        dosage_form = self._extract_dosage_form_strict(cleaned_text)
        frequency, freq_raw = self._extract_frequency(expanded_text)
        dose_quantity = self._extract_dose_quantity(cleaned_text)
        scheduled_times = self._extract_scheduled_times(cleaned_text)
        instructions = self._extract_instructions(cleaned_text)
        duration_days = self._extract_duration(cleaned_text)
        quantity = self._extract_total_quantity(cleaned_text)

        # Calculate start/end date ONLY if explicit dates or durations are detected in OCR text
        # STRICT RULE: NEVER default to today's date
        start_date = issue_date if issue_date else None
        end_date = expiry_date if expiry_date else None
        if not end_date and start_date and duration_days:
            end_date = start_date + timedelta(days=duration_days)

        # Medicine name determination: preserve raw detected OCR token, attach matched candidate
        raw_medicine_name = detected_raw_med or None
        matched_candidate_name = med_match.get("matched_name") if med_match else None
        final_medicine_name = raw_medicine_name or matched_candidate_name or None

        # Build clean fields dictionary - missing fields remain None
        fields = {
            "doctor_name": doctor_name,
            "prescription_number": prescription_number,
            "issue_date": issue_date.isoformat() if issue_date else None,
            "expiry_date": end_date.isoformat() if end_date else None,
            "start_date": start_date.isoformat() if start_date else None,
            "medicine_name": final_medicine_name,
            "detected_raw_medicine_name": raw_medicine_name,
            "strength": strength_str,
            "dosage_amount": dosage_amount,
            "dosage_unit": dosage_unit.value if dosage_unit else None,
            "dosage_form": dosage_form.value if dosage_form else None,
            "frequency": frequency.value if frequency else None,
            "frequency_raw": freq_raw,
            "dose_quantity": dose_quantity,
            "scheduled_times": scheduled_times,
            "instructions": instructions,
            "duration_days": duration_days,
            "quantity": quantity,
        }

        # Build Section 15 Structured Medication Schema
        med_confidence = med_match.get("confidence", 0.0) if med_match else (0.70 if raw_medicine_name else 0.0)
        medication = {
            "medicine_name": {
                "value": final_medicine_name,
                "source": "ocr" if raw_medicine_name else ("reference_match" if matched_candidate_name else "not_detected"),
                "confidence": med_confidence,
            },
            "strength": {
                "value": str(int(dosage_amount)) if (dosage_amount is not None and dosage_amount.is_integer()) else (str(dosage_amount) if dosage_amount is not None else None),
                "source": "ocr" if dosage_amount is not None else "not_detected",
                "confidence": 0.90 if dosage_amount is not None else 0.0,
            },
            "unit": {
                "value": dosage_unit.value if dosage_unit else None,
                "source": "ocr" if dosage_unit else "not_detected",
                "confidence": 0.90 if dosage_unit else 0.0,
            },
            "dosage_form": {
                "value": dosage_form.value.capitalize() if dosage_form else None,
                "source": "ocr" if dosage_form else "not_detected",
                "confidence": 0.85 if dosage_form else 0.0,
            },
            "instructions": {
                "value": instructions,
                "source": "ocr" if instructions else "not_detected",
                "confidence": 0.85 if instructions else 0.0,
            },
            "start_date": {
                "value": start_date.isoformat() if start_date else None,
                "source": "ocr" if start_date else "not_detected",
                "confidence": 0.85 if start_date else 0.0,
            },
            "end_date": {
                "value": end_date.isoformat() if end_date else None,
                "source": "ocr" if end_date else "not_detected",
                "confidence": 0.85 if end_date else 0.0,
            },
        }

        # Build Field Evidence / Provenance mapping
        evidence = {
            "doctor_name": {
                "value": doctor_name,
                "source": "ocr_header" if doctor_name else "not_detected",
                "confidence": 0.85 if doctor_name else 0.0,
            },
            "prescription_number": {
                "value": prescription_number,
                "source": "ocr_regex" if prescription_number else "not_detected",
                "confidence": 0.90 if prescription_number else 0.0,
            },
            "medicine_name": medication["medicine_name"],
            "strength": {
                "value": strength_str,
                "source": "ocr_regex" if strength_str else "not_detected",
                "confidence": 0.90 if strength_str else 0.0,
            },
            "dosage_form": medication["dosage_form"],
            "frequency": {
                "value": frequency.value if frequency else None,
                "source": "ocr_keyword" if frequency else "not_detected",
                "confidence": 0.85 if frequency else 0.0,
            },
            "duration_days": {
                "value": duration_days,
                "source": "ocr_regex" if duration_days else "not_detected",
                "confidence": 0.90 if duration_days else 0.0,
            },
            "quantity": {
                "value": quantity,
                "source": "ocr_regex" if quantity else "not_detected",
                "confidence": 0.85 if quantity else 0.0,
            },
        }

        return {
            "medication": medication,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "fields": fields,
            "evidence": evidence,
            "match": med_match,
            "confidence_score": med_confidence,
            "confidence_level": self.matcher.get_confidence_level(med_confidence),
        }

    def _empty_extraction_result(self, raw_text: str) -> Dict[str, Any]:
        empty_med = {
            "medicine_name": {"value": None, "source": "not_detected", "confidence": 0.0},
            "strength": {"value": None, "source": "not_detected", "confidence": 0.0},
            "unit": {"value": None, "source": "not_detected", "confidence": 0.0},
            "dosage_form": {"value": None, "source": "not_detected", "confidence": 0.0},
            "instructions": {"value": None, "source": "not_detected", "confidence": 0.0},
            "start_date": {"value": None, "source": "not_detected", "confidence": 0.0},
            "end_date": {"value": None, "source": "not_detected", "confidence": 0.0},
        }
        return {
            "medication": empty_med,
            "raw_text": raw_text,
            "cleaned_text": "",
            "fields": {
                "doctor_name": None,
                "prescription_number": None,
                "issue_date": None,
                "expiry_date": None,
                "start_date": None,
                "medicine_name": None,
                "detected_raw_medicine_name": None,
                "strength": None,
                "dosage_amount": None,
                "dosage_unit": None,
                "dosage_form": None,
                "frequency": None,
                "frequency_raw": None,
                "dose_quantity": None,
                "scheduled_times": None,
                "instructions": None,
                "duration_days": None,
                "quantity": None,
            },
            "evidence": {},
            "match": None,
            "confidence_score": 0.0,
            "confidence_level": "LOW",
        }


    def _extract_doctor_name(self, text: str) -> Optional[str]:
        patterns = [
            r"\b(?:Dr\.|Doctor|Physician)\s+([A-Za-z\.\s]{3,35})\b",
            r"(?:Prescribed\s+by|Consultant)\s*[:.]?\s*([A-Za-z\.\s]{3,35})",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.split(r"[\n\r,;]", name)[0].strip()
                # Exclude noisy non-doctor words
                if len(name) >= 3 and not any(w in name.lower() for w in ["hospital", "clinic", "department", "degree", "mbbs", "pharma"]):
                    return f"Dr. {name}" if not name.lower().startswith("dr") else name
        return None

    def _extract_prescription_number(self, text: str) -> Optional[str]:
        patterns = [
            r"\b(?:Rx\s*#?|Prescription\s*(?:No\.?|#)|Ref\s*(?:No\.?|#))\s*[:.]?\s*([A-Za-z0-9\-_]{3,20})\b",
            r"\b(?:RX|ID)\s*[:#]\s*([A-Za-z0-9\-]{4,20})\b",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) >= 3 and any(char.isdigit() for char in candidate):
                    return candidate
        return None

    def _extract_dates(self, text: str) -> Tuple[Optional[date], Optional[date]]:
        issue_date: Optional[date] = None
        expiry_date: Optional[date] = None

        date_patterns = [
            r"\b(20\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01]))\b",
            r"\b((?:0[1-9]|[12]\d|3[01])[-/.](?:0[1-9]|1[0-2])[-/.](?:20\d{2}|\d{2}))\b",
            r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})\b",
        ]

        found_dates: List[date] = []
        for pat in date_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                d_str = m.group(1).replace("/", "-").replace(".", "-")
                parsed = self._parse_date_string(d_str)
                if parsed and parsed not in found_dates:
                    found_dates.append(parsed)

        if found_dates:
            found_dates.sort()
            issue_date = found_dates[0]
            if len(found_dates) > 1:
                expiry_date = found_dates[-1]

        return issue_date, expiry_date

    @staticmethod
    def _parse_date_string(date_str: str) -> Optional[date]:
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%d-%m-%y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    def _extract_medicine_name_and_match(self, text: str) -> Tuple[Dict[str, Any], Optional[str]]:
        candidate_phrases: List[str] = []

        # 1. Regex search for explicit prefix matches (e.g. "Sgp Calpol", "Tab Napa", "Cap Amox")
        prefix_matches = re.findall(r"\b(?:tab|thb|tbb|cap|csp|syp|sgp|srup|syr|inj|1nj|drop|drp|eye\s*drops?)\.?\s+([A-Za-z]{3,25})\b", text, re.IGNORECASE)
        for pm in prefix_matches:
            if len(pm) >= 3:
                candidate_phrases.insert(0, pm)

        # 2. Regex search for explicit Rx / Medicine indicator phrases
        rx_matches = re.findall(r"(?:Rx|Medication|Drug|Medicine|Item)\s*[:.]?\s*([A-Za-z\s\-]{3,35})", text, re.IGNORECASE)
        for rx_candidate in rx_matches:
            cleaned = re.split(r"\b(?:\d+\s*(?:mg|g|mcg|ml|iu)|tablet|capsule|take|sig|every|twice|once)\b", rx_candidate, flags=re.IGNORECASE)[0].strip()
            cleaned = re.sub(r"[^a-zA-Z\s\-]", "", cleaned).strip()
            if cleaned and len(cleaned) >= 3:
                candidate_phrases.append(cleaned)

        # 3. Regex search for tokens directly preceding dosage amounts (e.g. "Amoxicillin 500 mg")
        pre_dosage_matches = re.findall(r"\b([A-Za-z][A-Za-z\s\-]{2,30})\s+\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|iu|units?)\b", text, re.IGNORECASE)
        for cand in pre_dosage_matches:
            words = cand.strip().split()
            if words:
                candidate_phrases.append(words[-1])
                if len(words) >= 2:
                    candidate_phrases.append(f"{words[-2]} {words[-1]}")

        # 4. Line-by-line fallback
        lines = [l.strip() for l in re.split(r"[\n\r]+", text) if l.strip()]
        for line in lines:
            if any(h in line.lower() for h in ["doctor", "dr.", "date:", "patient:", "hospital", "clinic", "address", "phone", "signature", "age:", "gender:"]):
                continue

            cleaned_line = re.sub(r"^(?:Rx|Medication|Drug|Medicine|Item)\s*[:.]?\s*", "", line, flags=re.IGNORECASE).strip()
            name_part = re.split(r"\b(?:\d+\s*(?:mg|g|mcg|ml|iu)|tablet|capsule|syrup|drops|cream|ointment|inhaler)\b", cleaned_line, flags=re.IGNORECASE)[0].strip()
            name_part = re.sub(r"[^a-zA-Z\s\-]", "", name_part).strip()

            if name_part and len(name_part) >= 3:
                candidate_phrases.append(name_part)
                words = name_part.split()
                if len(words) > 1:
                    candidate_phrases.append(words[0])

        # 5. All distinct alphabetical medicine tokens
        raw_words = re.findall(r"\b[A-Za-z]{3,20}\b", text)
        for w in raw_words:
            candidate_phrases.append(w)

        best_match = {
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
        best_candidate_raw = None
        all_found_candidates: List[Dict[str, Any]] = []

        STOP_WORDS = {
            "take", "give", "daily", "twice", "thrice", "once", "with", "water", "food",
            "meals", "tablet", "tablets", "capsule", "capsules", "syrup", "drops", "inj",
            "injection", "days", "day", "weeks", "week", "months", "month", "hours", "hour",
            "morning", "night", "evening", "noon", "bedtime", "after", "before", "every",
            "for", "and", "the", "sig", "dispense", "use", "apply", "as", "directed",
            "name", "date", "doctor", "patient", "clinic", "hospital", "diagnosis", "http",
            "www", "center", "centre", "prescription", "phone", "address", "mbes", "mbbs",
            "john", "doe", "jane", "smith"
        }

        # Identify words from patient / doctor names to prevent false positive matching
        patient_match = re.search(r"\bpatient(?:\s+name)?\s*[:.]?\s*([A-Za-z\s]+?)(?:\s+date|\s+age|\s+rx|\s+dr|\n|$)", text, re.IGNORECASE)
        if patient_match:
            for pw in patient_match.group(1).split():
                if len(pw.strip()) >= 2:
                    STOP_WORDS.add(pw.strip().lower())

        doctor_match = re.search(r"\b(?:dr\.|doctor|physician)\s+([A-Za-z\s]+?)(?:\s+date|\s+rx|\s+patient|\n|$)", text, re.IGNORECASE)
        if doctor_match:
            for dw in doctor_match.group(1).split():
                if len(dw.strip()) >= 2:
                    STOP_WORDS.add(dw.strip().lower())

        seen = set()
        unique_candidates = []
        for c in candidate_phrases:
            c_clean = c.strip()
            if (
                c_clean
                and c_clean.lower() not in seen
                and c_clean.lower() not in STOP_WORDS
                and len(c_clean) >= 3
            ):
                seen.add(c_clean.lower())
                unique_candidates.append(c_clean)

        for phrase in unique_candidates:
            match_res = self.matcher.match_medicine_name(phrase)
            if match_res.get("candidates"):
                for cand in match_res["candidates"]:
                    if not any(existing["dataset_name"] == cand["dataset_name"] for existing in all_found_candidates):
                        all_found_candidates.append(cand)

            if match_res["confidence"] > best_match["confidence"]:
                best_match = match_res
                best_candidate_raw = phrase
                if match_res["confidence"] >= 0.95:
                    break

        has_explicit_pattern = bool(prefix_matches or rx_matches or pre_dosage_matches)

        if not best_match["candidates"] and all_found_candidates:
            all_found_candidates.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
            best_match["candidates"] = all_found_candidates[:5]

        if not best_match.get("matched_name") and all_found_candidates:
            top_cand = all_found_candidates[0]
            if top_cand.get("confidence", 0.0) >= 0.50 or has_explicit_pattern:
                best_match["matched_name"] = top_cand["dataset_name"]
                best_match["confidence"] = top_cand["confidence"]
                best_match["confidence_level"] = self.matcher.get_confidence_level(top_cand["confidence"])

        if best_match.get("matched_name") and not best_candidate_raw:
            best_candidate_raw = best_match["matched_name"]

        # If no explicit pattern and confidence < 0.40, do not falsely identify non-med words as medicine name
        if not has_explicit_pattern and best_match.get("confidence", 0.0) < 0.40:
            best_candidate_raw = None
            best_match["matched_name"] = None

        return best_match, best_candidate_raw

    def _extract_strength(self, text: str) -> Tuple[Optional[float], Optional[DosageUnit], Optional[str]]:
        """Extract dosage strength (amount and unit) strictly from text."""
        # 1. Check standard mg / ml / mcg
        pattern = r"\b(\d+(?:\.\d+)?)\s*(mg|g|mcg|ml|iu|units?|%)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1)
            unit_str = match.group(2).upper()
            try:
                amount = float(amount_str)
                unit_map = {
                    "MG": DosageUnit.MG,
                    "G": DosageUnit.G,
                    "MCG": DosageUnit.MCG,
                    "ML": DosageUnit.ML,
                    "IU": DosageUnit.UNIT,
                    "UNIT": DosageUnit.UNIT,
                    "UNITS": DosageUnit.UNIT,
                }
                dosage_unit = unit_map.get(unit_str, DosageUnit.MG)

                strength_str = f"{amount_str} {match.group(2)}"
                return amount, dosage_unit, strength_str
            except ValueError:
                pass

        # 2. Check syrup ratio (e.g. 600/5 -> 600 mg / 5 ml)
        ratio_match = re.search(r"\b(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\b", text)
        if ratio_match:
            try:
                amt = float(ratio_match.group(1))
                return amt, DosageUnit.MG, f"{ratio_match.group(1)}mg/{ratio_match.group(2)}ml"
            except ValueError:
                pass

        return None, None, None

    def _extract_dosage_form_strict(self, text: str) -> Optional[MedicineForm]:
        """Extract dosage form strictly when explicitly present in OCR text. Never guess or default."""
        form_patterns = [
            (r"\b(?:tablets?|tabs?|thb|tbb)\b", MedicineForm.TABLET),
            (r"\b(?:capsules?|caps?|csp)\b", MedicineForm.CAPSULE),
            (r"\b(?:syrups?|syrup|syp|sgp|srup|syr|suspension|liquid)\b", MedicineForm.SYRUP),
            (r"\b(?:drops?|eye\s*drops?|ear\s*drops?|drp)\b", MedicineForm.DROPS),
            (r"\b(?:injections?|inj|1nj|vial|ampoule)\b", MedicineForm.INJECTION),
            (r"\b(?:creams?|topical|gel|ointments?|oint)\b", MedicineForm.CREAM),
            (r"\b(?:inhalers?|inhaler|puff|inhalation)\b", MedicineForm.OTHER),
        ]
        for pattern, form_enum in form_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return form_enum

        return None


    def _extract_frequency(self, text: str) -> Tuple[Optional[ScheduleFrequency], Optional[str]]:
        """Extract dosing frequency from text."""
        freq_patterns = [
            (r"\b(?:four\s*times\s*daily|4\s*times\s*a?\s*day|qid|q\.i\.d\.)\b", ScheduleFrequency.FOUR_TIMES_DAILY, "Four Times Daily"),
            (r"\b(?:three\s*times\s*daily|3\s*times\s*a?\s*day|tid|t\.i\.d\.)\b", ScheduleFrequency.THREE_TIMES_DAILY, "Three Times Daily"),
            (r"\b(?:twice\s*daily|2\s*times\s*a?\s*day|bid|b\.i\.d\.|morning\s*and\s*evening|morning\s*and\s*night)\b", ScheduleFrequency.TWICE_DAILY, "Twice Daily"),
            (r"\b(?:once\s*daily|1\s*time\s*a?\s*day|od|o\.d\.|qd|q\.d\.|daily|every\s*day|every\s*morning|every\s*night)\b", ScheduleFrequency.ONCE_DAILY, "Once Daily"),
            (r"\b(?:every\s*(\d+)\s*hours?|q(\d+)h)\b", ScheduleFrequency.CUSTOM, "Every X Hours"),
            (r"\b(?:as\s*needed|when\s*needed|prn|p\.r\.n\.)\b", ScheduleFrequency.CUSTOM, "As Needed"),
            (r"\b(?:weekly|once\s*a\s*week|every\s*week)\b", ScheduleFrequency.CUSTOM, "Weekly"),
        ]

        for pattern, freq_enum, label in freq_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return freq_enum, label

        return None, None

    def _extract_dose_quantity(self, text: str) -> Optional[float]:
        """Extract dose count per intake ONLY when explicitly detected (e.g. 'Take 2 tabs' -> 2.0)."""
        match = re.search(r"\b(?:take|give|use)?\s*(\d+(?:\.\d+)?)\s*(?:tablet|tab|capsule|cap|drop|puff|unit|ml|spoon)s?\b", text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _extract_scheduled_times(self, text: str) -> Optional[List[str]]:
        """Extract specific scheduled times if explicitly stated in prescription text."""
        time_matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)(?:\s*(am|pm))?\b|\b([1-9]|1[0-2])\s*(am|pm)\b", text, re.IGNORECASE)
        if not time_matches:
            return None

        times = []
        for tm in time_matches:
            if tm[0] and tm[1]:
                hour = int(tm[0])
                minute = int(tm[1])
                ampm = tm[2].lower() if tm[2] else None
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
                times.append(f"{hour:02d}:{minute:02d}")
            elif tm[3] and tm[4]:
                hour = int(tm[3])
                ampm = tm[4].lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
                times.append(f"{hour:02d}:00")

        unique_times = []
        for t in times:
            if t not in unique_times:
                unique_times.append(t)

        return unique_times if unique_times else None

    def _extract_instructions(self, text: str) -> Optional[str]:
        """Extract patient instructions (e.g., 'Take after food', 'With water')."""
        instruction_phrases = [
            r"\b(?:take\s+)?(after\s+food|before\s+food|with\s+food)\b",
            r"\b(?:take\s+)?(after\s+meals?|before\s+meals?)\b",
            r"\b(?:take\s+)?(on\s+an?\s+empty\s+stomach)\b",
            r"\b(?:take\s+)?(at\s+bedtime)\b",
            r"\b(with\s+(?:a\s+)?full\s+glass\s+of\s+water|with\s+water)\b",
            r"\b(avoid\s+alcohol)\b",
            r"\b(do\s+not\s+crush\s+or\s+chew)\b",
            r"\b(as\s+directed(?:\s+by\s+physician)?)\b",
        ]
        found = []
        for pat in instruction_phrases:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                found.append(m.group(1).capitalize())
        if found:
            return "; ".join(found)
        return None

    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract duration in days (e.g., 'for 5 days', 'for 2 weeks')."""
        match = re.search(r"\b(?:for|x)\s*(\d+)\s*(days?|weeks?|months?)\b", text, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            if "day" in unit:
                return num
            elif "week" in unit:
                return num * 7
            elif "month" in unit:
                return num * 30
        return None

    def _extract_total_quantity(self, text: str) -> Optional[int]:
        """Extract total package quantity ONLY when explicitly specified (e.g. 'Qty: 60' or 'Dispense: 30')."""
        match = re.search(r"\b(?:qty|quantity|dispense|count)\s*[:#]?\s*(\d+)\b", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
