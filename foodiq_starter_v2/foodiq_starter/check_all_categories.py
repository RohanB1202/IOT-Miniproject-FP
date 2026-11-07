import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent

print("\n========== FOODIQ SYSTEM AUDIT ==========\n")

# 1. Inspect standards configuration
rules_path = BASE / "quality_rules.json"

with open(rules_path, "r", encoding="utf-8") as f:
    rules = json.load(f)

categories = {
    "milk": "Milk quality",
    "fermented": "Fermented products",
    "fruit_beverage": "Fruits and beverages"
}

for key, label in categories.items():
    config = rules.get(key, {})

    print(f"\n--- {label} ---")
    print("Enabled:", config.get("enabled", False))
    print("Source:", config.get("source", "Missing"))
    print("Reviewed by:", config.get("reviewed_by", "Missing"))
    print("Hard limits:", len(config.get("hard_limits", [])))
    print("Quality criteria:", len(config.get("criteria", {})))

# 2. Inspect AI model files
print("\n========== AI MODEL AUDIT ==========\n")

models = [
    "milk_model.joblib",
    "fermented_model.joblib",
    "fruit_beverage_model.joblib"
]

for model in models:
    path = BASE / "models" / model
    print(model, "FOUND" if path.exists() else "NOT FOUND")

# 3. Inspect dataset templates
print("\n========== DATASET AUDIT ==========\n")

datasets = [
    "sample_training_template.csv",
    "quality_dataset_template.csv"
]

for filename in datasets:
    path = BASE / filename

    print("\nFile:", filename)

    if path.exists():
        df = pd.read_csv(path)
        print("Rows:", len(df))
        print("Columns:", list(df.columns))
    else:
        print("File not found")

print("\n========== AUDIT COMPLETE ==========")