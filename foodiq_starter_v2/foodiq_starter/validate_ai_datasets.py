from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).parent
DATA_DIR = BASE / "ai_datasets"

DATASETS = {
    "milk": {
        "file": "milk_training_template.csv",
        "numeric": ["fat_pct", "snf_pct", "ph",
                    "titratable_acidity_pct_lactic_acid",
                    "density_kg_m3", "milk_temperature_c"],
    },
    "fermented": {
        "file": "fermented_training_template.csv",
        "numeric": ["ph", "acidity_pct_lactic_acid", "fat_pct",
                    "total_solids_pct", "fermentation_hours",
                    "storage_temperature_c", "storage_duration_hours"],
    },
    "fruit_beverage": {
        "file": "fruit_beverage_training_template.csv",
        "numeric": ["tss_brix", "ph", "acidity_pct",
                    "firmness_n", "weight_loss_pct", "fruit_content_pct",
                    "storage_temperature_c", "storage_duration_hours"],
    },
}
REQUIRED = ["record_id", "batch_id", "sample_date", "product_type",
            "expert_grade", "reviewed_by", "reviewer_qualification",
            "label_basis", "review_date", "evidence_verified",
            "reference_standard", "measurement_methods",
            "grade_rationale", "safety_concerns"]
ALLOWED_GRADES = {"A", "B", "C", "HOLD"}

def main():
    reports = []
    print("\n========== FOODIQ DATASET VALIDATION ==========")
    for category, config in DATASETS.items():
        path = DATA_DIR / config["file"]
        print(f"\n--- {category.upper()} ---")
        issues = []
        if not path.exists():
            issues.append("Dataset file not found")
            df = pd.DataFrame()
        else:
            df = pd.read_csv(path)

        missing_cols = [c for c in REQUIRED if c not in df.columns]
        if missing_cols:
            issues.append("Missing required columns: " + ", ".join(missing_cols))
        if df.empty:
            # Empty datasets are expected until verified expert labels are collected.
            if not missing_cols:
                print("No verified expert labels yet; dataset is safely empty.")

        eligible = 0
        if not df.empty and not missing_cols:
            for field in REQUIRED:
                missing = df[field].isna() | df[field].astype(str).str.strip().eq("")
                if missing.any():
                    issues.append(f"{field}: {int(missing.sum())} missing")

            verified = df["evidence_verified"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])
            if not verified.all():
                issues.append("Some rows have not been marked evidence_verified")

            grades = df["expert_grade"].astype(str).str.strip().str.upper()
            invalid_grades = sorted(set(grades) - ALLOWED_GRADES)
            if invalid_grades:
                issues.append("Invalid expert_grade values: " + ", ".join(invalid_grades))

            for key in ["record_id", "batch_id"]:
                vals = df[key].dropna().astype(str).str.strip()
                if vals.duplicated().any():
                    issues.append(f"Duplicate {key} values")

            for field in ["sample_date", "review_date"]:
                dates = pd.to_datetime(df[field], errors="coerce")
                bad = df[field].notna() & df[field].astype(str).str.strip().ne("") & dates.isna()
                if bad.any():
                    issues.append(f"{field}: {int(bad.sum())} invalid dates")

            for field in config["numeric"]:
                if field not in df.columns:
                    issues.append(f"Missing measurement column: {field}")
                    continue
                populated = df[field].notna() & df[field].astype(str).str.strip().ne("")
                values = pd.to_numeric(df[field], errors="coerce")
                bad = populated & (values.isna() | ~np.isfinite(values))
                if bad.any():
                    issues.append(f"{field}: {int(bad.sum())} invalid numeric values")

            complete = pd.Series(True, index=df.index)
            for field in REQUIRED:
                complete &= df[field].notna() & df[field].astype(str).str.strip().ne("")
            eligible = int(complete.sum())

        status = "STRUCTURALLY VALID" if not issues else "NEEDS ATTENTION"
        print("Rows:", len(df))
        print("Rows with complete review metadata:", eligible)
        if issues:
            print("Findings:")
            for issue in issues:
                print(" -", issue)
        else:
            print("No structural validation issues.")
        reports.append({"category": category, "status": status,
                        "rows": len(df), "eligible_rows": eligible,
                        "issues": "; ".join(issues) if issues else "None"})

    report = pd.DataFrame(reports)
    report_path = DATA_DIR / "validation_report.csv"
    report.to_csv(report_path, index=False)
    print("\n========== SUMMARY ==========")
    print(report.to_string(index=False))
    print("\nSaved:", report_path)

if __name__ == "__main__":
    main()
