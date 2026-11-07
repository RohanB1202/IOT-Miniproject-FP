"""Train and evaluate a decision-tree classifier for the FOODIQ test dataset.

This workflow is deliberately separate from ``train_all_models.py`` and does
not overwrite ``models/milk_model.joblib``.  The target is a deterministic
FSSAI composition-screen result, so this model is useful only for test/demo
purposes; the rules remain the authoritative compliance screen.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier, export_text


BASE = Path(__file__).parent
DATA_PATH = BASE / "ai_datasets" / "fssai_milk_quality_dataset.csv"
MODEL_PATH = BASE / "models" / "fssai_decision_tree_demo.joblib"
REPORT_DIR = BASE / "reports"
METRICS_PATH = REPORT_DIR / "fssai_decision_tree_demo_metrics.json"
CONFUSION_PATH = REPORT_DIR / "fssai_decision_tree_demo_confusion_matrix.csv"
TREE_PATH = REPORT_DIR / "fssai_decision_tree_demo_rules.txt"

TARGET = "fssai_composition_result"
NUMERIC_FEATURES = [
    "fat_pct",
    "snf_pct",
    "total_sodium_mg_per_100g_snf",
    "total_urea_ppm",
]
CATEGORICAL_FEATURES = ["milk_class"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
LABELS = ["PASS", "HOLD"]
RANDOM_STATE = 42


def build_model() -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            ("numeric", "passthrough", NUMERIC_FEATURES),
            ("milk_class", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    tree = DecisionTreeClassifier(
        criterion="gini",
        max_depth=8,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight={"PASS": 1, "HOLD": 2},
        random_state=RANDOM_STATE,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", tree)])


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    missing = [column for column in FEATURES + [TARGET] if column not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    if set(df[TARGET].dropna().unique()) != set(LABELS):
        raise ValueError(f"{TARGET} must contain exactly: {LABELS}")

    X = df[FEATURES].copy()
    y = df[TARGET].copy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE
    )
    model = build_model()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    held_out_metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "balanced_accuracy": balanced_accuracy_score(y_test, predictions),
        "hold_precision": precision_score(y_test, predictions, pos_label="HOLD", zero_division=0),
        "hold_recall": recall_score(y_test, predictions, pos_label="HOLD", zero_division=0),
        "hold_f1": f1_score(y_test, predictions, pos_label="HOLD", zero_division=0),
        "pass_recall": recall_score(y_test, predictions, pos_label="PASS", zero_division=0),
    }
    report = classification_report(y_test, predictions, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_test, predictions, labels=LABELS)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "hold_precision": make_scorer(precision_score, pos_label="HOLD", zero_division=0),
        "hold_recall": make_scorer(recall_score, pos_label="HOLD", zero_division=0),
        "hold_f1": make_scorer(f1_score, pos_label="HOLD", zero_division=0),
    }
    cv_results = cross_validate(build_model(), X, y, cv=cv, scoring=scoring, n_jobs=-1)
    cv_metrics = {
        name: {
            "mean": float(cv_results[f"test_{name}"].mean()),
            "std": float(cv_results[f"test_{name}"].std()),
        }
        for name in scoring
    }

    MODEL_PATH.parent.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    artifact = {
        "model": model,
        "features": FEATURES,
        "target": TARGET,
        "classes": LABELS,
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics": held_out_metrics,
        "cross_validation": cv_metrics,
        "data_source": str(DATA_PATH.name),
        "limitation": (
            "Test/demo model only. Its labels are rule-derived, so it must not replace "
            "the FSSAI composition screen or be used for production food-safety decisions."
        ),
    }
    joblib.dump(artifact, MODEL_PATH)

    metrics = {
        "dataset": DATA_PATH.name,
        "rows": int(len(df)),
        "features": FEATURES,
        "target": TARGET,
        "tree_parameters": model.named_steps["classifier"].get_params(),
        "held_out_test": held_out_metrics,
        "cross_validation_5_fold": cv_metrics,
        "classification_report": report,
        "confusion_matrix_labels": LABELS,
        "limitation": artifact["limitation"],
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame(matrix, index=[f"actual_{label}" for label in LABELS],
                 columns=[f"predicted_{label}" for label in LABELS]).to_csv(CONFUSION_PATH)

    transformed_names = model.named_steps["preprocessor"].get_feature_names_out()
    TREE_PATH.write_text(
        export_text(model.named_steps["classifier"], feature_names=list(transformed_names)),
        encoding="utf-8",
    )

    print("FOODIQ FSSAI DECISION-TREE DEMO")
    print(f"Rows: {len(df)} | Train: {len(X_train)} | Test: {len(X_test)}")
    print("Held-out metrics:")
    for name, value in held_out_metrics.items():
        print(f"  {name}: {value:.4f}")
    print("Confusion matrix (rows=actual, columns=predicted; PASS, HOLD):")
    print(matrix)
    print(f"Model: {MODEL_PATH}")
    print(f"Metrics: {METRICS_PATH}")


if __name__ == "__main__":
    main()
