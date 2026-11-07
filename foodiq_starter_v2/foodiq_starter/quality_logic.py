"""Rule-based quality assessment. Populate quality_rules.json only from verified standards.

The code deliberately does not invent FSSAI limits. Regulatory failures override
quality grades; project A/B/C bands are separate from mandatory limits.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

RULES_PATH = Path(__file__).with_name("quality_rules.json")


def load_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return {}
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _inside(value: float, bounds: dict[str, Any]) -> bool:
    lo, hi = bounds.get("min"), bounds.get("max")
    return (lo is None or value >= float(lo)) and (hi is None or value <= float(hi))


def assess(category: str, product_type: str, values: dict[str, Any]) -> dict[str, Any]:
    """Return configured regulatory status and operational grade, if available.

    quality_rules.json structure per product:
      {"regulatory_limits": {"parameter": {"min": x, "max": y,
          "mandatory": true, "source": "..."}},
       "grade_bands": {"parameter": {"A": {"min": x, "max": y}, ...}}}
    For a parameter where lower is better, set the min/max band ranges accordingly.
    Final overall grade is the weakest grade among configured grade parameters.
    """
    product_rules = load_rules().get(category, {}).get(product_type, {})
    if not product_rules:
        return {"status": "NOT CONFIGURED", "grade": None,
                "reason": "No verified product-specific limits have been configured."}

    failures = []
    for key, limit in product_rules.get("regulatory_limits", {}).items():
        if not limit.get("mandatory", True):
            continue
        raw = values.get(key)
        if raw in (None, ""):
            return {"status": "INCOMPLETE", "grade": None,
                    "reason": f"Required regulatory parameter missing: {key}."}
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return {"status": "INCOMPLETE", "grade": None,
                    "reason": f"Invalid value for required parameter: {key}."}
        if not _inside(val, limit):
            failures.append(f"{key}={val} outside the configured mandatory limit")
    if failures:
        return {"status": "NON-COMPLIANT / HOLD", "grade": None,
                "reason": "; ".join(failures)}

    grades = []
    for key, bands in product_rules.get("grade_bands", {}).items():
        raw = values.get(key)
        if raw in (None, ""):
            return {"status": "INCOMPLETE", "grade": None,
                    "reason": f"Required grading parameter missing: {key}."}
        val = float(raw)
        matched = None
        for grade in ("C", "B", "A"):
            if grade in bands and _inside(val, bands[grade]):
                matched = grade
                break
        if matched is None:
            return {"status": "OUTSIDE CONFIGURED GRADING BANDS", "grade": None,
                    "reason": f"{key}={val} does not fit any configured grade band."}
        grades.append(matched)

    if not grades:
        return {"status": "REGULATORY CHECK PASSED", "grade": None,
                "reason": "No operational A/B/C grading bands have been configured."}
    overall = min(grades, key=lambda g: {"A": 0, "B": 1, "C": 2}[g])
    return {"status": "CHECKED AGAINST CONFIGURED RULES", "grade": overall,
            "reason": "Overall grade uses the weakest grade across configured parameters."}
