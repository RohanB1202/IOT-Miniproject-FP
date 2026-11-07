from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
OUTPUT = BASE / "ai_datasets"
OUTPUT.mkdir(exist_ok=True)

COMMON = [
    "record_id",
    "batch_id",
    "sample_date",
    "product_type",
    "supplier",
    "laboratory_method",
]

REVIEW_FIELDS = [
    "expert_grade",
    "reviewed_by",
    "reviewer_qualification",
    "label_basis",
    "review_date",
    "review_notes",
]

TEMPLATES = {
    "milk": COMMON + [
        "milk_category",
        "fat_pct",
        "snf_pct",
        "ph",
        "titratable_acidity_pct_lactic_acid",
        "density_kg_m3",
        "milk_temperature_c",
        "alcohol_test",
        "clot_on_boiling_test",
        "starch_screen",
        "urea_screen",
        "detergent_screen",
        "neutralizer_screen",
        "colour",
        "odour",
        "appearance",
        "consistency",
    ] + REVIEW_FIELDS,

    "fermented": COMMON + [
        "ph",
        "acidity_pct_lactic_acid",
        "fat_pct",
        "total_solids_pct",
        "fermentation_hours",
        "texture",
        "syneresis",
        "odour",
        "storage_temperature_c",
        "storage_duration_hours",
    ] + REVIEW_FIELDS,

    "fruit_beverage": COMMON + [
        "product_category",
        "tss_brix",
        "ph",
        "acidity_pct",
        "firmness_n",
        "weight_loss_pct",
        "fruit_content_pct",
        "ripeness",
        "bruising",
        "appearance",
        "package_integrity",
        "storage_temperature_c",
        "storage_duration_hours",
    ] + REVIEW_FIELDS,
}

print("\n========== FOODIQ TRAINING TEMPLATES ==========")

for category, columns in TEMPLATES.items():
    filename = OUTPUT / f"{category}_training_template.csv"

    df = pd.DataFrame(columns=columns)
    df.to_csv(filename, index=False)

    print(f"\nCreated: {filename.name}")
    print("Columns:", len(columns))
    print("Initial data rows:", len(df))

print("\nAll three templates created successfully.")