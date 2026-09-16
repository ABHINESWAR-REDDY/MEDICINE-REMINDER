"""OCR Text Preprocessing and Normalization Module.

Handles cleaning of raw OCR artifacts, whitespace normalization,
and context-aware character corrections for dosage and clinical text.
"""

import re


class OCRTextPreprocessor:
    """Preprocesses and cleans raw text extracted by OCR engine."""

    # Common medical/dosage unit patterns
    UNIT_PATTERN = r"(?:mg|g|mcg|ml|iu|units?|tablets?|capsules?|drops?|pills?)"

    # Common abbreviations dictionary
    ABBREVIATION_MAP = {
        r"\bb\.?i\.?d\.?\b": "Twice Daily",
        r"\bt\.?i\.?d\.?\b": "Three Times Daily",
        r"\bq\.?i\.?d\.?\b": "Four Times Daily",
        r"\bo\.?d\.?\b": "Once Daily",
        r"\bq\.?d\.?\b": "Once Daily",
        r"\bq\.?h\.?s\.?\b": "At Bedtime",
        r"\bh\.?s\.?\b": "At Bedtime",
        r"\bp\.?r\.?n\.?\b": "As Needed",
        r"\bstat\b": "Immediately",
        r"\btab\b": "Tablet",
        r"\bcaps?\b": "Capsule",
        r"\bsyr\b": "Syrup",
        r"\binj\b": "Injection",
        r"\bpo\b": "By Mouth",
        r"\bp\.?o\.?\b": "By Mouth",
    }

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """
        Normalize raw text from OCR:
        - Removes non-printable control characters
        - Standardizes line breaks and whitespace
        - Contextually repairs common OCR character confusion (e.g. 50O mg -> 500 mg)
        """
        if not raw_text:
            return ""

        # Normalize line endings
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove non-printable/weird control characters, keeping common punctuation and newlines
        text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)

        # Context-aware digit repair: 'O' or 'o' surrounded by or adjacent to digits or before units
        # e.g., "50O mg" -> "500 mg", "1O0" -> "100", "O.5 mg" -> "0.5 mg"
        text = re.sub(r"(?<=\d)[Oo](?=\d|\s*" + cls.UNIT_PATTERN + r"|\b)", "0", text, flags=re.IGNORECASE)
        text = re.sub(r"(?<=\b)[Oo](?=\.\d+)", "0", text)
        text = re.sub(r"(?<=\b)[Oo](?=\d)", "0", text)

        # Context-aware digit repair: 'l' or 'I' as '1' when immediately before units or between digits
        # e.g., "l0 mg" -> "10 mg", "I00 mg" -> "100 mg", "5l0 mg" -> "510 mg"
        text = re.sub(r"(?<=\d)[lI](?=\d)", "1", text)
        text = re.sub(r"\b[lI](?=\d+\s*" + cls.UNIT_PATTERN + r"\b)", "1", text, flags=re.IGNORECASE)
        text = re.sub(r"\b[lI](?=\s*" + cls.UNIT_PATTERN + r"\b)", "1", text, flags=re.IGNORECASE)

        # Fix spacing between numbers and common units (e.g. 500mg -> 500 mg)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(" + cls.UNIT_PATTERN + r")\b", r"\1 \2", text, flags=re.IGNORECASE)

        # Clean excessive spaces per line while preserving meaningful line breaks
        lines = []
        for line in text.split("\n"):
            cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
            if cleaned_line:
                lines.append(cleaned_line)

        return "\n".join(lines)

    @classmethod
    def expand_abbreviations(cls, text: str) -> str:
        """Expand common Latin prescription abbreviations."""
        if not text:
            return ""
        expanded = text
        for pattern, replacement in cls.ABBREVIATION_MAP.items():
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        return expanded
