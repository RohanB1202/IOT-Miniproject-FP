"""Create a milk-composition test dataset for the FOODIQ development environment.

The rule screen implements the composition requirements in FSSAI FPS&FA
Regulations, 2011, sub-regulation 2.1.2, as reproduced in the FSSAI dairy
compendium (Version XXV, 23 September 2022): fat and SNF are evaluated
independently; sodium must be <=650 mg/100 g SNF and total urea <=700 ppm.
The Gazette notifications and later amendments remain authoritative.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


BASE = Path(__file__).parent
OUTPUT = BASE / "ai_datasets" / "fssai_milk_quality_dataset.csv"
SEED = 20261104
ROWS_PER_CLASS = 120

# ``fat_max`` applies only to skimmed milk; every other class has a minimum.
STANDARDS = {
    "Buffalo Milk": {"fat_min": 5.0, "fat_max": None, "snf_min": 9.0, "raw": True},
    "Cow Milk": {"fat_min": 3.2, "fat_max": None, "snf_min": 8.3, "raw": True},
    "Goat or Sheep Milk": {"fat_min": 3.0, "fat_max": None, "snf_min": 8.0, "raw": True},
    "Camel Milk": {"fat_min": 2.0, "fat_max": None, "snf_min": 6.0, "raw": True},
    "Mixed Milk": {"fat_min": 4.5, "fat_max": None, "snf_min": 8.5, "raw": True},
    "Standardized Milk": {"fat_min": 4.5, "fat_max": None, "snf_min": 8.5, "raw": False},
    "Toned Milk": {"fat_min": 3.0, "fat_max": None, "snf_min": 8.5, "raw": False},
    "Double Toned Milk": {"fat_min": 1.5, "fat_max": None, "snf_min": 9.0, "raw": False},
    "Skimmed Milk": {"fat_min": None, "fat_max": 0.5, "snf_min": 8.7, "raw": False},
    "Full Cream Milk": {"fat_min": 6.0, "fat_max": None, "snf_min": 9.0, "raw": False},
}

FIELDS = [
    "record_id", "batch_id", "sample_date",
    "milk_class", "milk_category", "heat_treatment", "fat_pct", "snf_pct",
    "total_sodium_mg_per_100g_snf", "total_urea_ppm", "ph",
    "titratable_acidity_pct_lactic_acid", "density_kg_m3", "milk_temperature_c",
    "fssai_min_fat_pct", "fssai_max_fat_pct", "fssai_min_snf_pct",
    "fssai_max_sodium_mg_per_100g_snf", "fssai_max_urea_ppm",
    "fssai_composition_result", "failure_reasons",
]


def rounded(value: float, digits: int = 2) -> float:
    return round(value, digits)


def passing_fat(rule: dict[str, float | bool | None], rng: random.Random) -> float:
    if rule["fat_max"] is not None:
        return rounded(rng.uniform(0.08, float(rule["fat_max"])))
    return rounded(float(rule["fat_min"]) + rng.uniform(0.03, 1.35))


def failing_fat(rule: dict[str, float | bool | None], rng: random.Random) -> float:
    if rule["fat_max"] is not None:
        return rounded(float(rule["fat_max"]) + rng.uniform(0.02, 0.65))
    return rounded(max(0.05, float(rule["fat_min"]) - rng.uniform(0.03, 0.9)))


def assess(row: dict[str, object]) -> tuple[str, str]:
    """Return a composition-screen result, never an FSSAI A/B/C quality grade."""
    reasons: list[str] = []
    if row["fssai_min_fat_pct"] is not None and row["fat_pct"] < row["fssai_min_fat_pct"]:
        reasons.append("fat below class minimum")
    if row["fssai_max_fat_pct"] is not None and row["fat_pct"] > row["fssai_max_fat_pct"]:
        reasons.append("fat above class maximum")
    if row["snf_pct"] < row["fssai_min_snf_pct"]:
        reasons.append("SNF below class minimum")
    if row["total_sodium_mg_per_100g_snf"] > row["fssai_max_sodium_mg_per_100g_snf"]:
        reasons.append("total sodium above maximum")
    if row["total_urea_ppm"] > row["fssai_max_urea_ppm"]:
        reasons.append("total urea above maximum")
    if reasons:
        return "HOLD", "; ".join(reasons)
    return "PASS", "Within the configured composition screen."


def make_row(record_id: int, milk_class: str, rule: dict[str, float | bool | None], rng: random.Random) -> dict[str, object]:
    # The fixed mix deliberately includes pass and distinct failure cases for UI/model demos.
    scenario = record_id % 20
    fat = passing_fat(rule, rng)
    snf = rounded(float(rule["snf_min"]) + rng.uniform(0.03, 1.10))
    sodium = rounded(rng.uniform(120, 640), 1)
    urea = rounded(rng.uniform(40, 690), 1)
    if scenario in {14, 15}:
        fat = failing_fat(rule, rng)
    elif scenario in {16, 17}:
        snf = rounded(max(0.1, float(rule["snf_min"]) - rng.uniform(0.03, 0.8)))
    elif scenario == 18:
        sodium = rounded(rng.uniform(651, 900), 1)
    elif scenario == 19:
        urea = rounded(rng.uniform(701, 950), 1)

    start = date(2026, 1, 1)
    row: dict[str, object] = {
        "record_id": f"FSSAI-{record_id:04d}",
        "batch_id": f"MILK-{milk_class.replace(' ', '-').upper()}-{record_id:04d}",
        "sample_date": (start + timedelta(days=record_id % 365)).isoformat(),
        "milk_class": milk_class,
        "milk_category": "Raw milk" if rule["raw"] else "Processed milk",
        "heat_treatment": "Not heat treated" if rule["raw"] else "Pasteurised",
        "fat_pct": fat,
        "snf_pct": snf,
        "total_sodium_mg_per_100g_snf": sodium,
        "total_urea_ppm": urea,
        "ph": rounded(rng.uniform(6.45, 6.85)),
        "titratable_acidity_pct_lactic_acid": rounded(rng.uniform(0.11, 0.20), 3),
        "density_kg_m3": rounded(rng.uniform(1025, 1035), 1),
        "milk_temperature_c": rounded(rng.uniform(3.0, 8.0), 1),
        "fssai_min_fat_pct": rule["fat_min"],
        "fssai_max_fat_pct": rule["fat_max"],
        "fssai_min_snf_pct": rule["snf_min"],
        "fssai_max_sodium_mg_per_100g_snf": 650,
        "fssai_max_urea_ppm": 700,
    }
    row["fssai_composition_result"], row["failure_reasons"] = assess(row)
    return row


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    record_id = 1
    for milk_class, rule in STANDARDS.items():
        for _ in range(ROWS_PER_CLASS):
            rows.append(make_row(record_id, milk_class, rule, rng))
            record_id += 1
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["fssai_composition_result"] == "PASS" for row in rows)
    held = len(rows) - passed
    print(f"Wrote {len(rows)} records to {OUTPUT}")
    print(f"Composition screen: {passed} passed, {held} hold scenarios")


if __name__ == "__main__":
    main()
