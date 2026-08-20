"""
Field-level normalization helpers.

Design principle: NEVER destroy the original value. Every normalizer
returns (normalized_value, raw_value_preserved_elsewhere) so downstream
code and the data-quality report can always show "what we started with"
next to "what we cleaned it to". This is what the assignment calls
"notice and handle [messiness] -- not crash on it, and not silently
invent values".
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Contractor name normalization
# ---------------------------------------------------------------------------

_MS_PREFIX_RE = re.compile(r"\bM/[Ss]\b\.?", re.IGNORECASE)
_QUOTE_CHARS_RE = re.compile(r'["\u201c\u201d\u2018\u2019]')
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_contractor(raw: Optional[str]) -> Optional[str]:
    """
    Normalize a contractor string:
    - strip stray quote characters
    - collapse duplicated 'M/S' / 'M/s' prefixes into a single 'M/S'
    - collapse internal whitespace
    - title-case for consistent grouping (comparison only; raw is preserved
      separately by the caller)

    Multiple contractors sometimes appear concatenated in one cell
    (e.g. two firms on a joint contract). We keep the full string but
    normalize each 'M/S' occurrence, rather than guessing which name is
    "the real one" -- guessing would be exactly the kind of invented
    value the assignment forbids.
    """
    if raw is None or not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None

    text = _QUOTE_CHARS_RE.sub("", text)
    # Collapse any run of M/S-like tokens (possibly duplicated) to one "M/S "
    text = _MS_PREFIX_RE.sub("M/S", text)
    # If "M/S" appears more than once, keep only the first occurrence as a
    # prefix and drop subsequent bare repeats immediately followed by another
    # "M/S" further firm name (this handles "M/S M/S Firm A M/S Firm B").
    text = re.sub(r"(M/S\s*)+", "M/S ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text if text else None


# ---------------------------------------------------------------------------
# Executing agency normalization
# ---------------------------------------------------------------------------

# Documented, explicit mapping only -- we do NOT use fuzzy matching to merge
# names automatically, because silently merging two agencies that only
# *look* similar would risk misattributing spend. Instead we group known
# textual variants of the SAME agency that appear in this dataset.
AGENCY_VARIANT_GROUPS: dict[str, list[str]] = {
    "Local Government": ["LG", "Local Govt", "LGRD", "MC LG"],
    "Public Health Engineering": ["PHE", "PHED"],
    "Communication & Works / Public Health & Prov. Physical Planning & Housing": [
        "CWPP&H", "C&WPP&H",
    ],
}

_AGENCY_VARIANT_LOOKUP: dict[str, str] = {
    variant.strip().upper(): canonical
    for canonical, variants in AGENCY_VARIANT_GROUPS.items()
    for variant in variants
}


def normalize_agency(raw: Optional[str]) -> Optional[str]:
    """Map a known variant string to its canonical agency name.
    Unknown values are returned unchanged (trimmed) -- we never invent a
    canonical name for an agency we don't have a documented mapping for."""
    if raw is None or not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    canonical = _AGENCY_VARIANT_LOOKUP.get(text.upper())
    return canonical if canonical else text


# ---------------------------------------------------------------------------
# Phone number normalization
# ---------------------------------------------------------------------------

def normalize_phone(raw) -> tuple[Optional[str], bool]:
    """
    Normalize a Pakistani mobile/landline number to E.164-ish '92XXXXXXXXXX'
    where confidently possible.

    Returns (normalized_or_none, needs_review).

    Handles observed formats:
      - '3345417779'            (10 digits, missing leading 0/92)
      - '0333-3773307'          (dashed, leading 0)
      - '9.23328E+11'           (Excel scientific notation string)
      - '923327891347'          (already E.164 without '+')
      - '3,337,717,516'         (comma-grouped, thousands-style)

    We NEVER invent digits. If after cleaning we don't have a plausible
    11-12 digit Pakistani number, we return the cleaned digits with
    needs_review=True rather than guessing.
    """
    if raw is None:
        return None, False
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None, False

    # Excel scientific notation, e.g. "9.23328E+11"
    if re.match(r"^\d+(\.\d+)?[eE]\+?\d+$", text):
        try:
            as_int = int(float(text))
            text = str(as_int)
        except (ValueError, OverflowError):
            return text, True

    # Strip commas, spaces, dashes, parentheses
    digits = re.sub(r"[^\d]", "", text)

    if not digits:
        return raw if isinstance(raw, str) else str(raw), True

    # Normalize to leading '92' country code form
    if digits.startswith("92") and len(digits) == 12:
        normalized = digits
    elif digits.startswith("0") and len(digits) == 11:
        normalized = "92" + digits[1:]
    elif len(digits) == 10:
        normalized = "92" + digits
    else:
        # Doesn't match any confidently-recognized pattern -- flag it.
        return digits, True

    # Basic plausibility: Pakistani mobile numbers are 92 + 10 digits = 12 digits total
    if len(normalized) != 12:
        return normalized, True

    formatted = f"+{normalized[:2]}-{normalized[2:5]}-{normalized[5:]}"
    return formatted, False


# ---------------------------------------------------------------------------
# Numeric cleaning
# ---------------------------------------------------------------------------

def safe_float(value) -> Optional[float]:
    """Convert to float; return None (not 0, not a guess) on failure."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if value == "" or value.lower() == "nan":
                return None
        return float(value)
    except (ValueError, TypeError):
        return None
