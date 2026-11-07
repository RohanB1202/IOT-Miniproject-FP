# Copy this script into a Google Colab notebook cell-by-cell, or upload it to Colab.
# Train ONE model per module (milk, fermented, or fruit_beverage).
# Only use real, independently labelled laboratory/QC records.

import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# 1) Upload quality_dataset.csv in Colab, then set the file path below.
DATA_PATH = "/content/quality_dataset.csv"
MODULE_TO_TRAIN = "milk"  # change to fermented or fruit_beverage

# 2) Choose features that are actually measured in this module.
# Do not include grade, batch_id, record_id, operator, or timestamps as predictors.
FEATURES_BY_MODULE = {
    "milk": ["temperature_c", "humidity_pct", "mq2_raw", "mq135_raw", "fat_pct", "snf_pct", "ph", "titratable_acidity_pct_lactic_acid", "density_kg_m3"],
    "fermented": ["temperature_c", "humidity_pct", "mq2_raw", "mq135_raw", "ph", "acidity_pct_lactic_acid", "fat_pct", "total_solids_pct", "fermentation_hours"],
    "fruit_beverage": ["temperature_c", "humidity_pct", "mq2_raw", "mq135_raw", "tss_brix", "ph", "acidity_pct", "firmness_n", "weight_loss_pct"],
}

# 3) Load and filter data.
df = pd.read_csv(DATA_PATH)
df = df[df["module"].astype(str).str.lower() == MODULE_TO_TRAIN].copy()
FEATURES = FEATURES_BY_MODULE[MODULE_TO_TRAIN]
required = ["batch_id", "grade"] + FEATURES
missing_columns = [c for c in required if c not in df.columns]
if missing_columns:
    raise ValueError(f"Missing columns in dataset: {missing_columns}")

df["grade"] = df["grade"].astype(str).str.upper().str.strip()
df = df[df["grade"].isin(["A", "B", "C"])].copy()
for col in FEATURES:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Discard rows with no usable predictor data and rows without batch IDs.
df = df.dropna(subset=["batch_id", "grade"])
df = df[df[FEATURES].notna().any(axis=1)]
print("Rows:", len(df))
print("Grade counts:\n", df["grade"].value_counts())
print("Distinct batches:", df["batch_id"].nunique())

if df["grade"].nunique() < 2:
    raise ValueError("At least two labelled grades are required to train a classifier.")
if df["batch_id"].nunique() < 5:
    raise ValueError("Collect more independent batches before evaluating a model. Five batches is only a minimal technical check, not a sufficient validation standard.")

X = df[FEATURES]
y = df["grade"]
groups = df["batch_id"].astype(str)

# 4) Split by batch, not randomly by individual measurement rows.
# This reduces leakage from repeated readings of the same batch.
splitter = GroupShuffleSplit(n_splits=30, test_size=0.20, random_state=42)
chosen_split = None
all_classes = set(y.unique())
for train_idx, test_idx in splitter.split(X, y, groups):
    if set(y.iloc[train_idx].unique()) == all_classes and set(y.iloc[test_idx].unique()) == all_classes:
        chosen_split = (train_idx, test_idx)
        break
if chosen_split is None:
    raise ValueError("Could not create a batch-independent split containing every grade in train and test. Collect more batches for each grade.")
train_idx, test_idx = chosen_split
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

# 5) Train an interpretable baseline model.
preprocess = ColumnTransformer(
    transformers=[("numeric", SimpleImputer(strategy="median"), FEATURES)],
    remainder="drop",
)
model = Pipeline([
    ("preprocess", preprocess),
    ("classifier", RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=42,
        min_samples_leaf=2,
    )),
])
model.fit(X_train, y_train)
pred = model.predict(X_test)

# 6) Evaluate honestly on unseen batches.
print("Accuracy:", round(accuracy_score(y_test, pred), 3))
print("Confusion matrix (labels A, B, C):")
print(confusion_matrix(y_test, pred, labels=["A", "B", "C"]))
print(classification_report(y_test, pred, labels=["A", "B", "C"], zero_division=0))

# 7) Save artifact for Streamlit.
artifact = {"model": model, "features": FEATURES, "module": MODULE_TO_TRAIN}
output_path = f"/content/{MODULE_TO_TRAIN}_model.joblib"
joblib.dump(artifact, output_path)
print("Saved:", output_path)

# 8) Download the .joblib file from Colab and place it in the Streamlit project's models/ folder.
from google.colab import files
files.download(output_path)
