import sqlite3
import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
DB_PATH = BASE / "foodiq.db"
DATA_DIR = BASE / "ai_datasets"

TEMPLATES = {
    "milk": "milk_training_template.csv",
    "fermented": "fermented_training_template.csv",
    "fruit_beverage": "fruit_beverage_training_template.csv",
}

# Only fields present in the relevant template are exported.
COMMON_MAP = {
    "record_id": "record_id",
    "batch_id": "batch_id",
    "sample_date": "created_at",
    "product_type": "product_type",
}
MODULE_MAP = {
    "milk": {
        "supplier": "supplier_source",
        "milk_category": "milk_category",
        "fat_pct": "fat_pct",
        "snf_pct": "snf_pct",
        "ph": "ph",
        "titratable_acidity_pct_lactic_acid": "titratable_acidity_pct_lactic_acid",
        "density_kg_m3": "density_kg_m3",
        "milk_temperature_c": "milk_temperature_c",
        "alcohol_test": "alcohol_test",
        "clot_on_boiling_test": "clot_on_boiling_test",
        "starch_screen": "starch_screen",
        "urea_screen": "urea_screen",
        "detergent_screen": "detergent_screen",
        "neutralizer_screen": "neutralizer_screen",
        "colour": "colour",
        "odour": "odour",
        "appearance": "appearance",
        "consistency": "consistency",
    },
    "fermented": {
        "supplier": "supplier_source",
        "ph": "ph",
        "acidity_pct_lactic_acid": "acidity_pct_lactic_acid",
        "fat_pct": "fat_pct",
        "total_solids_pct": "total_solids_pct",
        "fermentation_hours": "fermentation_hours",
        "texture": "texture",
        "syneresis": "syneresis",
        "odour": "odour",
        "storage_temperature_c": "storage_temperature_c",
        "storage_duration_hours": "storage_duration_hours",
    },
    "fruit_beverage": {
        "supplier": "supplier_source",
        "product_category": "product_category",
        "tss_brix": "tss_brix",
        "ph": "ph",
        "acidity_pct": "acidity_pct",
        "firmness_n": "firmness_n",
        "weight_loss_pct": "weight_loss_pct",
        "fruit_content_pct": "fruit_content_pct",
        "ripeness": "ripeness",
        "bruising": "bruising",
        "appearance": "appearance",
        "package_integrity": "package_integrity",
        "storage_temperature_c": "storage_temperature_c",
        "storage_duration_hours": "storage_duration_hours",
    },
}
REVIEW_FIELDS = [
    "expert_grade", "reviewed_by", "reviewer_qualification",
    "label_basis", "review_date", "review_notes", "evidence_verified",
    "reference_standard", "measurement_methods", "grade_rationale", "safety_concerns",
]

def main():
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        rows = pd.read_sql_query("""
            SELECT o.id AS record_id, o.batch_id, o.module, o.product_type,
                   o.created_at, o.payload,
                   r.expert_grade, r.reviewed_by, r.reviewer_qualification,
                   r.label_basis, r.review_date, r.review_notes,
                   r.evidence_verified, r.reference_standard, r.measurement_methods,
                   r.grade_rationale, r.safety_concerns, r.observation_id
            FROM observations o
            LEFT JOIN expert_reviews r ON r.observation_id = o.id
            ORDER BY o.id
        """, conn)

    print("FOODIQ EXPERT-LABELLED DATASET PREPARATION")
    print("Database observations:", len(rows))
    print("Joined expert reviews:", int(rows["expert_grade"].notna().sum()) if not rows.empty else 0)

    for module, filename in TEMPLATES.items():
        template_path = DATA_DIR / filename
        if template_path.exists():
            columns = list(pd.read_csv(template_path, nrows=0).columns)
            for evidence_col in ["evidence_verified", "reference_standard", "measurement_methods",
                                 "grade_rationale", "safety_concerns"]:
                if evidence_col not in columns:
                    columns.append(evidence_col)
        else:
            raise FileNotFoundError(f"Template not found: {template_path}")

        subset = rows[rows["module"] == module].copy()
        output = []

        for _, rec in subset.iterrows():
            try:
                payload = json.loads(rec["payload"] or "{}")
            except (TypeError, ValueError):
                print(f"Skipping observation {rec['record_id']}: invalid JSON payload")
                continue

            row = {col: None for col in columns}
            for col, source in COMMON_MAP.items():
                value = rec.get(source)
                if col == "sample_date" and value:
                    value = str(value)[:10]
                row[col] = value

            for col, source in MODULE_MAP[module].items():
                row[col] = payload.get(source)

            for col in REVIEW_FIELDS:
                row[col] = rec.get(col)

            output.append(row)

        result = pd.DataFrame(output, columns=columns)
        # Export reviewed observations to the training template. Keep unreviewed
        # observations in the separate observation audit file.
        reviewed = result[
            result["expert_grade"].notna()
            & result["expert_grade"].astype(str).str.strip().ne("")
            & result["evidence_verified"].fillna(0).astype(bool)
        ].copy()

        result.to_csv(DATA_DIR / f"{module}_observations.csv", index=False)
        reviewed.to_csv(template_path, index=False)

        print(f"\n{module}:")
        print("  Observations:", len(result))
        print("  Expert-reviewed rows exported:", len(reviewed))
        print("  Training dataset:", template_path.name)
        if len(reviewed):
            print("  Grade counts:")
            print(reviewed["expert_grade"].value_counts(dropna=False).to_string())
    print("\nPreparation complete.")

if __name__ == "__main__":
    main()
