from pathlib import Path
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix

BASE = Path(__file__).parent
DATA_DIR = BASE / "ai_datasets"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(exist_ok=True)

CONFIG = {
    "milk": {
        "file": "milk_training_template.csv",
        "features": ["fat_pct", "snf_pct", "ph",
                     "titratable_acidity_pct_lactic_acid",
                     "density_kg_m3", "milk_temperature_c"],
    },
    "fermented": {
        "file": "fermented_training_template.csv",
        "features": ["ph", "acidity_pct_lactic_acid", "fat_pct",
                     "total_solids_pct", "fermentation_hours", "texture"],
    },
    "fruit_beverage": {
        "file": "fruit_beverage_training_template.csv",
        "features": ["tss_brix", "ph", "acidity_pct",
                     "firmness_n", "weight_loss_pct", "fruit_content_pct", "ripeness"],
    },
}
MINIMUM_SAMPLES = 30  # Prototype guardrail only; not a scientific sufficiency threshold.
MINIMUM_PER_CLASS = 5

def train_category(category, config):
    print(f"\n========== {category.upper()} ==========")
    path = DATA_DIR / config["file"]
    if not path.exists():
        print("SKIPPED: Dataset not found.")
        return

    df = pd.read_csv(path)
    needed = config["features"] + ["expert_grade"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print("SKIPPED: Missing columns:", missing)
        return

    df["expert_grade"] = df["expert_grade"].astype(str).str.strip().str.upper()
    df = df[df["expert_grade"].isin(["A", "B", "C", "HOLD"])].copy()
    if len(df) < MINIMUM_SAMPLES:
        print(f"SKIPPED: {len(df)} labelled samples; prototype guardrail is {MINIMUM_SAMPLES}.")
        return

    X = df[config["features"]].copy()
    y = df["expert_grade"]
    counts = y.value_counts()
    if y.nunique() < 2 or counts.min() < MINIMUM_PER_CLASS:
        print("SKIPPED: Need at least two classes and 5 examples in each class.")
        print(counts.to_string())
        return

    numeric = X.select_dtypes(include=["number"]).columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))

    model = Pipeline([
        ("preprocessor", ColumnTransformer(transformers)),
        ("classifier", RandomForestClassifier(
            n_estimators=200, random_state=42, class_weight="balanced"
        )),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    print("Accuracy:", accuracy_score(y_test, predictions))
    print("Precision:", precision_score(y_test, predictions, average="macro", zero_division=0))
    print("Recall:", recall_score(y_test, predictions, average="macro", zero_division=0))
    print("F1:", f1_score(y_test, predictions, average="macro", zero_division=0))
    print(classification_report(y_test, predictions, zero_division=0))
    print("Confusion matrix:\n", confusion_matrix(y_test, predictions))

    # FOODIQ app.py expects a dictionary with model and features.
    artifact = {
        "model": model,
        "features": config["features"],
        "classes": sorted(y.unique().tolist()),
        "metrics": {
            "accuracy": accuracy_score(y_test, predictions),
            "macro_precision": precision_score(y_test, predictions, average="macro", zero_division=0),
            "macro_recall": recall_score(y_test, predictions, average="macro", zero_division=0),
            "macro_f1": f1_score(y_test, predictions, average="macro", zero_division=0),
        },
        "training_rows": int(len(df)),
        "note": "Prototype model; requires independent validation before operational use.",
    }
    output = MODEL_DIR / f"{category}_model.joblib"
    joblib.dump(artifact, output)
    print("Saved FOODIQ-compatible model artifact:", output)

def main():
    print("FOODIQ AI TRAINING ENGINE")
    for category, config in CONFIG.items():
        train_category(category, config)
    print("\n========== TRAINING PROCESS COMPLETE ==========")

if __name__ == "__main__":
    main()
