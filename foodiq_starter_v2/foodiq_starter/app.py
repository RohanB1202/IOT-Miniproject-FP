import json
import os
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether
)

import joblib
import pandas as pd
import requests
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "foodiq.db"
RULES_PATH = APP_DIR / "quality_rules.json"
MODEL_DIR = APP_DIR / "models"
FSSAI_DEMO_MODEL_PATH = MODEL_DIR / "fssai_decision_tree_demo.joblib"

st.set_page_config(page_title="FOODIQ | Food Quality Intelligence", page_icon="🥛", layout="wide")

MODULES = {
    "Milk quality": {
        "key": "milk",
        "fields": [
            ("fat_pct", "Fat (%)"),
            ("snf_pct", "SNF (%)"),
            ("ph", "pH"),
            ("titratable_acidity_pct_lactic_acid", "Titratable acidity (% lactic acid)"),
            ("density_kg_m3", "Density (kg/m³)"),
        ],
        "choices": ["colour", "odour", "appearance"],
    },
    "Fermented products": {
        "key": "fermented",
        "fields": [
            ("ph", "pH"),
            ("acidity_pct_lactic_acid", "Titratable acidity (% lactic acid)"),
            ("fat_pct", "Fat (%)"),
            ("total_solids_pct", "Total solids (%)"),
            ("fermentation_hours", "Fermentation time (hours)"),
        ],
        "choices": ["texture", "syneresis", "odour"],
    },
    "Fruits and beverages": {
        "key": "fruit_beverage",
        "fields": [
            ("tss_brix", "TSS (°Brix)"),
            ("ph", "pH"),
            ("acidity_pct", "Titratable acidity (%)"),
            ("firmness_n", "Firmness (N; for fruits)"),
            ("weight_loss_pct", "Weight loss (%)"),
        ],
        "choices": ["ripeness", "bruising", "appearance", "package_integrity"],
    },
}

def build_milk_pdf(values, batch_id, product_type,
                   rule_grade, rule_explanation,
                   ai_grade, ai_error, ai_confidence):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "FoodIQTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#176B57"),
        spaceAfter=5
    )

    subtitle_style = ParagraphStyle(
        "FoodIQSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=16
    )

    section_style = ParagraphStyle(
        "FoodIQSection",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#176B57"),
        spaceBefore=12,
        spaceAfter=6
    )

    story = []

    def safe(value):
        return escape(str(value if value not in (None, "") else "Not provided"))

    def add_section(title, rows):
        story.append(Paragraph(title, section_style))

        table_data = [
            [Paragraph("<b>Parameter</b>", styles["BodyText"]),
             Paragraph("<b>Recorded value</b>", styles["BodyText"])]
        ]

        for label, value in rows:
            table_data.append([
                Paragraph(safe(label), styles["BodyText"]),
                Paragraph(safe(value), styles["BodyText"])
            ])

        table = Table(table_data, colWidths=[75 * mm, 100 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5F1ED")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D7D4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
        ]))

        story.append(table)

    story.append(Paragraph("FOODIQ", title_style))
    story.append(Paragraph("MILK QUALITY ASSESSMENT REPORT", subtitle_style))
    story.append(Paragraph(
        f"Report generated: {datetime.now().astimezone().strftime('%d-%m-%Y %H:%M')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 8))

    add_section("1. Sample identification", [
        ("Batch ID", batch_id),
        ("Milk category", values.get("milk_category")),
        ("Milk type", product_type),
        ("Supplier", values.get("supplier_source")),
        ("Sampling location", values.get("collection_location")),
        ("Sample reference", values.get("sample_reference"))
    ])

    add_section("2. Laboratory measurements", [
        ("Fat (%)", values.get("fat_pct")),
        ("SNF (%)", values.get("snf_pct")),
        ("pH", values.get("ph")),
        ("Titratable acidity (% lactic acid)",
         values.get("titratable_acidity_pct_lactic_acid")),
        ("Density (kg/m3)", values.get("density_kg_m3"))
    ])

    add_section("3. Stability and adulteration screening", [
        ("Alcohol stability", values.get("alcohol_test")),
        ("Clot-on-boiling", values.get("clot_on_boiling_test")),
        ("Starch", values.get("starch_screen")),
        ("Urea", values.get("urea_screen")),
        ("Detergent", values.get("detergent_screen")),
        ("Neutralizer", values.get("neutralizer_screen"))
    ])

    add_section("4. Sensory observations", [
        ("Colour", values.get("colour")),
        ("Odour", values.get("odour")),
        ("Appearance", values.get("appearance")),
        ("Consistency", values.get("consistency"))
    ])

    add_section("5. Storage and handling", [
        ("Storage condition", values.get("storage_type")),
        ("Storage duration (hours)", values.get("storage_duration_hours")),
        ("Milk temperature (C)", values.get("milk_temperature_c")),
        ("Storage temperature (C)", values.get("storage_temperature_c")),
        ("Storage humidity (%)", values.get("storage_humidity_pct")),
        ("Container", values.get("container_type"))
    ])

    snapshot = values.get("iot_snapshot", {})

    add_section("6. Connected IoT readings", [
        ("Ambient humidity (%)", snapshot.get("humidity_pct")),
        ("Ambient temperature (C)", snapshot.get("temperature_c")),
        ("MQ2 raw response", snapshot.get("mq2_raw")),
        ("MQ135 raw response", snapshot.get("mq135_raw"))
    ])

    add_section("7. Assessment results", [
        ("Rule-based result", rule_grade),
        ("Rule explanation", rule_explanation),
        ("AI result", ai_grade if ai_grade is not None else "Not available"),
        ("AI status", ai_error or "No additional error reported"),
        ("AI confidence", f"{ai_confidence:.1%}" if ai_confidence is not None else "Not available")
    ])

    add_section("8. Additional remarks", [
        ("Remarks", values.get("remarks"))
    ])

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<b>Important disclaimer:</b> This report is generated by a development "
        "prototype. It is not an accredited laboratory certificate or a food-safety "
        "release decision. IoT sensor readings are environmental/raw sensor data "
        "and do not independently establish milk composition or adulteration. "
        "Regulatory compliance requires verified standards and appropriate "
        "validated testing.",
        styles["BodyText"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
def secret_value(section, key, env_name=None, default=""):
    try:
        value = st.secrets.get(section, {}).get(key, default)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(env_name or key.upper(), default)




def read_expert_reviews():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """SELECT er.*, o.batch_id, o.module, o.product_type, o.created_at AS sample_created_at,
                      o.payload
               FROM expert_reviews er JOIN observations o ON o.id = er.observation_id
               ORDER BY er.review_date DESC, er.id DESC""", conn)


def save_expert_review(observation_id, grade, reviewer, qualification, basis, review_date, notes, evidence_verified, reference_standard, measurement_methods, grade_rationale, safety_concerns):
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO expert_reviews
               (observation_id, expert_grade, reviewed_by, reviewer_qualification,
                label_basis, review_date, review_notes, created_at,
                evidence_verified, reference_standard, measurement_methods,
                grade_rationale, safety_concerns)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(observation_id) DO UPDATE SET
                 expert_grade=excluded.expert_grade, reviewed_by=excluded.reviewed_by,
                 reviewer_qualification=excluded.reviewer_qualification,
                 label_basis=excluded.label_basis, review_date=excluded.review_date,
                 review_notes=excluded.review_notes, created_at=excluded.created_at,
                 evidence_verified=excluded.evidence_verified,
                 reference_standard=excluded.reference_standard,
                 measurement_methods=excluded.measurement_methods,
                 grade_rationale=excluded.grade_rationale,
                 safety_concerns=excluded.safety_concerns""",
            (int(observation_id), grade, reviewer.strip(), qualification.strip(),
             basis.strip(), str(review_date), notes.strip(), now,
             int(bool(evidence_verified)), reference_standard.strip(),
             measurement_methods.strip(), grade_rationale.strip(),
             safety_concerns.strip()))
        conn.commit()


def build_labelled_dataset(module_key):
    names = {"milk":"milk_training_template.csv",
             "fermented":"fermented_training_template.csv",
             "fruit_beverage":"fruit_beverage_training_template.csv"}
    template_path = APP_DIR / "ai_datasets" / names[module_key]
    if not template_path.exists():
        raise FileNotFoundError(f"Training template not found: {template_path}")
    columns = list(pd.read_csv(template_path).columns)
    with sqlite3.connect(DB_PATH) as conn:
        records = pd.read_sql_query(
            """SELECT o.id, o.batch_id, o.product_type, o.created_at, o.payload,
                      er.expert_grade, er.reviewed_by, er.reviewer_qualification,
                      er.label_basis, er.review_date, er.review_notes,
                      er.evidence_verified, er.reference_standard, er.measurement_methods,
                      er.grade_rationale, er.safety_concerns
               FROM observations o JOIN expert_reviews er ON er.observation_id=o.id
                WHERE o.module=?
                AND COALESCE(er.evidence_verified, 0)=1
                AND er.expert_grade IN ('A', 'B', 'C', 'HOLD')
                ORDER BY o.id""", conn, params=(module_key,))
    output = []
    for _, rec in records.iterrows():
        payload = json.loads(rec["payload"] or "{}")
        row = {c: None for c in columns}
        row.update({
            "record_id": int(rec["id"]), "batch_id": rec["batch_id"],
            "sample_date": str(rec["created_at"])[:10],
            "product_type": payload.get("milk_product_type") or rec["product_type"],
            "supplier": payload.get("supplier_source", ""),
            "laboratory_method": payload.get("laboratory_method", ""),
            "expert_grade": rec["expert_grade"], "reviewed_by": rec["reviewed_by"],
            "reviewer_qualification": rec["reviewer_qualification"],
            "label_basis": rec["label_basis"], "review_date": rec["review_date"],
            "review_notes": rec["review_notes"] or "",
            "evidence_verified": bool(rec["evidence_verified"]),
            "reference_standard": rec["reference_standard"] or "",
            "measurement_methods": rec["measurement_methods"] or "",
            "grade_rationale": rec["grade_rationale"] or "",
            "safety_concerns": rec["safety_concerns"] or ""})
        for col in columns:
            if col in payload:
                row[col] = payload[col]
        output.append(row)
    return pd.DataFrame(output, columns=columns)


def validate_labelled_dataset(df):
    issues = []
    if df.empty:
        return ["No expert-reviewed records are available for this module."]
    required = ["record_id","batch_id","product_type","expert_grade","reviewed_by",
                "reviewer_qualification","label_basis","review_date",
                "evidence_verified","reference_standard","measurement_methods",
                "grade_rationale","safety_concerns"]
    for col in required:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")
        elif df[col].isna().any() or (df[col].astype(str).str.strip()=="").any():
            issues.append(f"Missing values found in required field: {col}")
    if "expert_grade" in df.columns:
        invalid = sorted(set(df["expert_grade"].dropna().astype(str))-{"A","B","C","HOLD"})
        if invalid:
            issues.append("Invalid expert_grade labels: "+", ".join(invalid))
    if "record_id" in df.columns and df["record_id"].duplicated().any():
        issues.append("Duplicate record_id values found.")
    return issues

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                module TEXT NOT NULL,
                product_type TEXT,
                operator TEXT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT NOT NULL,
                rule_result TEXT,
                ai_result TEXT,
                ai_confidence REAL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS expert_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_id INTEGER NOT NULL UNIQUE,
                expert_grade TEXT NOT NULL,
                reviewed_by TEXT NOT NULL,
                reviewer_qualification TEXT NOT NULL,
                label_basis TEXT NOT NULL,
                review_date TEXT NOT NULL,
                review_notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(observation_id) REFERENCES observations(id)
            )"""
        )
        # Safe, additive migration for structured expert-evidence fields.
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(expert_reviews)").fetchall()
        }
        migrations = {
            "evidence_verified": "INTEGER NOT NULL DEFAULT 0",
            "reference_standard": "TEXT NOT NULL DEFAULT ''",
            "measurement_methods": "TEXT NOT NULL DEFAULT ''",
            "grade_rationale": "TEXT NOT NULL DEFAULT ''",
            "safety_concerns": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE expert_reviews ADD COLUMN {column} {definition}")
        conn.commit()


def fetch_thingspeak(results=20):
    channel_id = secret_value("thingspeak", "channel_id", "THINGSPEAK_CHANNEL_ID")
    read_key = secret_value("thingspeak", "read_api_key", "THINGSPEAK_READ_API_KEY")
    if not channel_id:
        return pd.DataFrame(), "ThingSpeak Channel ID is not configured."

    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
    params = {"results": results}
    if read_key:
        params["api_key"] = read_key
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        feeds = response.json().get("feeds", [])
        df = pd.DataFrame(feeds)
        if df.empty:
            return df, "No readings returned by ThingSpeak."

        # Default mapping based on this project's serial data order:
        # humidity, temperature, MQ2, MQ135. Adjust these field names
        # if the ESP8266 firmware writes to a different ThingSpeak mapping.
        field_map = {
            "field1": "humidity_pct",
            "field2": "temperature_c",
            "field3": "mq2_raw",
            "field4": "mq135_raw",
        }
        df = df.rename(columns=field_map)
        for col in field_map.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df, None
    except requests.RequestException as exc:
        return pd.DataFrame(), f"Could not read ThingSpeak: {exc}"
    except (ValueError, TypeError) as exc:
        return pd.DataFrame(), f"Unexpected ThingSpeak response: {exc}"


def load_rules():
    if not RULES_PATH.exists():
        return {}
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def in_range(value, bounds):
    if value is None or pd.isna(value):
        return False
    low = bounds.get("min")
    high = bounds.get("max")
    return (low is None or value >= low) and (high is None or value <= high)


def fssai_milk_class(values):
    """Map the Milk Quality form selections to the decision-tree class names."""
    raw_types = {
        "Cow milk": "Cow Milk",
        "Buffalo milk": "Buffalo Milk",
        "Mixed milk": "Mixed Milk",
    }
    processed_types = {
        "Standardised milk": "Standardized Milk",
        "Toned milk": "Toned Milk",
        "Double toned milk": "Double Toned Milk",
        "Full cream milk": "Full Cream Milk",
        "Skimmed milk": "Skimmed Milk",
    }
    if values.get("milk_category") == "Raw milk":
        return raw_types.get(values.get("milk_product_type"))
    if values.get("milk_category") == "Processed milk":
        return processed_types.get(values.get("milk_product_type"))
    return None


def classify_by_rules(module_key, values):
    """Assess milk records without implying regulatory approval.

    When the rule set is disabled, stored composition limits are used only as
    reference checks. They cannot produce a regulatory compliance decision or
    an A/B/C grade. Failed screening results are surfaced as investigation flags.
    """
    config = load_rules().get(module_key, {})

    if module_key == "milk" and not config.get("enabled", False):
        # Screening flags are independent of composition reference checks.
        failed_screens = [
            label for field, label in [
                ("alcohol_test", "Alcohol stability test"),
                ("clot_on_boiling_test", "Clot-on-boiling test"),
                ("starch_screen", "Starch screening"),
                ("urea_screen", "Urea screening"),
                ("detergent_screen", "Detergent screening"),
                ("neutralizer_screen", "Neutralizer screening"),
            ]
            if values.get(field) == "Fail / suspected positive"
        ]
        inconclusive_screens = [
            label for field, label in [
                ("alcohol_test", "Alcohol stability test"),
                ("clot_on_boiling_test", "Clot-on-boiling test"),
                ("starch_screen", "Starch screening"),
                ("urea_screen", "Urea screening"),
                ("detergent_screen", "Detergent screening"),
                ("neutralizer_screen", "Neutralizer screening"),
            ]
            if values.get(field) == "Inconclusive"
        ]

        if failed_screens:
            return (
                "HOLD — SCREENING FLAG",
                "One or more screening tests were recorded as failed/suspected positive: "
                + ", ".join(failed_screens)
                + ". Segregate/hold the sample according to the site's procedure and arrange an appropriate confirmatory method. A screening result is not a final adulteration finding."
            )
        if inconclusive_screens:
            return (
                "REVIEW — INCONCLUSIVE SCREEN",
                "Inconclusive screening result(s): " + ", ".join(inconclusive_screens)
                + ". Repeat or confirm using a validated method. No safety clearance is implied."
            )

        # Only raw cow and raw buffalo reference checks are currently configured.
        if values.get("milk_category") != "Raw milk" or values.get("milk_product_type") not in {"Cow milk", "Buffalo milk"}:
            return (
                "REFERENCE NOT CONFIGURED",
                "No reference composition check is configured for this milk category/type. No compliance decision or A/B/C grade has been assigned."
            )

        reference_minima = {
            "Cow milk": {"fat_pct": 3.2, "snf_pct": 8.3},
            "Buffalo milk": {"fat_pct": 5.0, "snf_pct": 9.0},
        }
        minima = reference_minima[values["milk_product_type"]]
        missing = [field for field in minima if values.get(field) is None or pd.isna(values.get(field))]
        if missing:
            return (
                "INSUFFICIENT DATA — REFERENCE CHECK",
                "Missing measurement(s) required for the stored composition reference check: "
                + ", ".join(missing)
                + ". Record valid laboratory results before interpreting the reference comparison."
            )

        deviations = []
        for field, minimum in minima.items():
            try:
                measured = float(values[field])
            except (TypeError, ValueError):
                return "INSUFFICIENT DATA — REFERENCE CHECK", f"Invalid numeric result for {field}."
            if not pd.notna(measured):
                return "INSUFFICIENT DATA — REFERENCE CHECK", f"Invalid numeric result for {field}."
            if measured < minimum:
                deviations.append(f"{field}={measured:g} is below the stored reference minimum {minimum:g}")

        if deviations:
            return (
                "REFERENCE DEVIATION — CONFIRM",
                "Stored reference comparison only; not a legal compliance determination. "
                + "; ".join(deviations)
                + ". Verify sample identity, analytical method, calibration and repeat result; obtain independent regulatory/laboratory review before any disposition."
            )
        return (
            "REFERENCE CHECK — NO BELOW-MINIMUM VALUE",
            "The recorded fat and SNF values are at or above the stored reference minima. This is not a regulatory compliance certificate, safety clearance or FOODIQ A/B/C grade. Other applicable requirements and validated tests remain to be assessed."
        )

    if not config.get("enabled", False):
        return "Not configured", "No reviewed, product-specific rules are enabled for this module."

    # Mandatory compliance checks are independent of project-defined A/B/C grades.
    for check in config.get("hard_limits", []):
        applies_to_category = check.get("milk_category")
        applies_to_product = check.get("milk_product_type")
        if applies_to_category and values.get("milk_category") != applies_to_category:
            continue
        if applies_to_product and values.get("milk_product_type") != applies_to_product:
            continue
        field = check.get("field")
        if field not in values or values[field] is None:
            return "Insufficient data", f"Required measurement missing: {field}."
        if not in_range(values[field], check.get("allowed", {})):
            return "HOLD", check.get("reason", "A mandatory requirement was not met.")

    criteria = config.get("criteria", {})
    if not criteria:
        return "Insufficient rules", "No project-defined quality criteria have been configured."
    missing = [field for field in criteria if values.get(field) is None]
    if missing:
        return "Insufficient data", "Missing required measurements: " + ", ".join(missing)
    grade_a = all(in_range(values[field], item.get("grade_a", {})) for field, item in criteria.items())
    grade_b = all(in_range(values[field], item.get("grade_b", {})) for field, item in criteria.items())
    if grade_a:
        return "A", "All configured Grade A quality bands were met."
    if grade_b:
        return "B", "Grade A was not met, but all configured Grade B bands were met."
    return "C", "One or more configured quality measurements fell outside Grade B bands. Review the measurements."


def predict_with_model(module_key, values):
    model_path = MODEL_DIR / f"{module_key}_model.joblib"
    if module_key == "milk" and not model_path.exists() and FSSAI_DEMO_MODEL_PATH.exists():
        model_path = FSSAI_DEMO_MODEL_PATH
    if not model_path.exists():
        return None, None, "No trained model found for this section."
    try:
        artifact = joblib.load(model_path)
        model = artifact["model"]
        features = artifact["features"]
        row = {name: values.get(name) for name in features}
        if "milk_class" in row:
            row["milk_class"] = fssai_milk_class(values)
        missing = [name for name, value in row.items() if value is None or value == ""]
        if missing:
            return None, None, "Enter the model-required values: " + ", ".join(missing) + "."
        X = pd.DataFrame([row], columns=features)
        prediction = str(model.predict(X)[0])
        confidence = None
        if hasattr(model, "predict_proba"):
            confidence = float(max(model.predict_proba(X)[0]))
        return prediction, confidence, None
    except Exception as exc:
        return None, None, f"Model prediction failed: {exc}"


def save_observation(batch_id, module_key, product_type, operator, source, values, rule_result, ai_result, ai_confidence):
    created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO observations
            (batch_id, module, product_type, operator, created_at, source, payload, rule_result, ai_result, ai_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch_id, module_key, product_type, operator, created_at, source,
             json.dumps(values, ensure_ascii=False), rule_result, ai_result, ai_confidence),
        )
        conn.commit()


def read_history():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM observations ORDER BY id DESC", conn)


init_db()

st.title("FOODIQ")
st.caption("IoT-enabled food quality monitoring and grading prototype")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Open section", ["Dashboard", "Milk quality", "Data & history", "Expert Review & AI Data", "Standards and AI setup"])
    st.divider()
    st.caption("Prototype note: A/B/C grades are project-defined quality categories, not universal FSSAI grades.")

sensor_df, sensor_error = fetch_thingspeak(results=20)
latest_sensor = {}
if not sensor_df.empty:
    latest = sensor_df.iloc[-1]
    latest_sensor = {k: (None if pd.isna(v) else float(v)) for k, v in latest.items() if k in ["temperature_c", "humidity_pct", "mq2_raw", "mq135_raw"]}

if page == "Dashboard":
    st.subheader("Live monitoring dashboard")
    if sensor_error:
        st.info(sensor_error)
    if latest_sensor:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temperature", f"{latest_sensor.get('temperature_c', float('nan')):.1f} °C" if latest_sensor.get("temperature_c") is not None else "—")
        c2.metric("Relative humidity", f"{latest_sensor.get('humidity_pct', float('nan')):.1f} %" if latest_sensor.get("humidity_pct") is not None else "—")
        c3.metric("MQ2 raw value", f"{latest_sensor.get('mq2_raw'):.0f}" if latest_sensor.get("mq2_raw") is not None else "—")
        c4.metric("MQ135 raw value", f"{latest_sensor.get('mq135_raw'):.0f}" if latest_sensor.get("mq135_raw") is not None else "—")
        if "created_at" in sensor_df.columns:
            st.caption(f"Most recent ThingSpeak timestamp: {sensor_df.iloc[-1]['created_at']}")
        chart_cols = [c for c in ["temperature_c", "humidity_pct", "mq2_raw", "mq135_raw"] if c in sensor_df.columns]
        if chart_cols:
            st.line_chart(sensor_df.set_index("created_at")[chart_cols] if "created_at" in sensor_df.columns else sensor_df[chart_cols])
        st.dataframe(sensor_df.tail(10), use_container_width=True)
    else:
        st.warning("No live sensor data yet. Configure ThingSpeak credentials in .streamlit/secrets.toml or environment variables.")
        st.write("The dashboard expects ThingSpeak fields 1–4 to contain humidity, temperature, MQ2 and MQ135 respectively.")

    history = read_history()
    if not history.empty:
        st.subheader("Recent quality assessments")
        st.dataframe(history[["created_at", "batch_id", "module", "product_type", "rule_result", "ai_result"]].head(10), use_container_width=True)

elif page in MODULES:
    module = MODULES[page]
    module_key = module["key"]
    st.subheader(f"{page} — sample assessment")
    st.caption("Enter laboratory measurements and observations. Latest environmental readings are attached when available.")
    if latest_sensor:
        with st.expander("Latest connected hardware readings", expanded=True):
            st.json(latest_sensor)

    with st.form(f"form_{module_key}"):
        a, b = st.columns(2)
        batch_id = a.text_input("Batch ID *", placeholder="e.g. MILK-2026-001")
        operator = b.text_input("Operator / analyst")

        values = {}
        if module_key == "milk":
            st.markdown("### 1. Sample identification")
            c1, c2 = st.columns(2)
            milk_category = c1.selectbox("Milk category *", ["Raw milk", "Processed milk"])
            if milk_category == "Raw milk":
                product_type = c2.selectbox("Raw milk type *", ["Cow milk", "Buffalo milk", "Mixed milk", "Other raw milk"])
            else:
                product_type = c2.selectbox("Processed milk type *", ["Pasteurised milk", "Toned milk", "Double toned milk", "Standardised milk", "Full cream milk", "Skimmed milk", "Homogenised milk", "UHT milk", "Other processed milk"])
            source = st.text_input("Supplier / farm / processing unit", placeholder="Name or source code")
            collection_location = st.text_input("Collection / sampling location", placeholder="Farm, collection centre, processing line, etc.")
            sample_code = st.text_input("Laboratory sample reference", placeholder="Optional lab reference")

            st.markdown("### 2. Laboratory measurements")
            st.caption("Enter values from calibrated instruments or validated laboratory methods. Leave unmeasured values blank.")
            columns = st.columns(2)
            for index, (field, label) in enumerate(module["fields"]):
                raw = columns[index % 2].text_input(label, key=f"{module_key}_{field}", placeholder="Enter measured value")
                if raw.strip():
                    try:
                        values[field] = float(raw)
                    except ValueError:
                        st.warning(f"{label}: enter a numeric value.")
                        values[field] = None
                else:
                    values[field] = None

            fssai_columns = st.columns(2)
            for index, (field, label) in enumerate([
                ("total_sodium_mg_per_100g_snf", "Total sodium (mg per 100 g SNF)"),
                ("total_urea_ppm", "Total urea (ppm)"),
            ]):
                raw = fssai_columns[index].text_input(
                    label, key=f"{module_key}_{field}", placeholder="Enter measured value"
                )
                if raw.strip():
                    try:
                        values[field] = float(raw)
                    except ValueError:
                        st.warning(f"{label}: enter a numeric value.")
                        values[field] = None
                else:
                    values[field] = None

            st.markdown("### 3. Stability and adulteration screening")
            st.caption("These are recorded observations only. A screening result is not, by itself, a complete regulatory compliance certificate.")
            test_options = ["Not tested", "Pass / negative", "Fail / suspected positive", "Inconclusive"]
            test_fields = [
                ("alcohol_test", "Alcohol stability test"),
                ("clot_on_boiling_test", "Clot-on-boiling (COB) test"),
                ("starch_screen", "Starch screening"),
                ("urea_screen", "Urea screening"),
                ("detergent_screen", "Detergent screening"),
                ("neutralizer_screen", "Neutralizer screening"),
            ]
            test_cols = st.columns(2)
            for i, (field, label) in enumerate(test_fields):
                values[field] = test_cols[i % 2].selectbox(label, test_options, key=f"milk_{field}")

            st.markdown("### 4. Sensory and visual observations")
            choice_labels = {"colour": "Colour", "odour": "Odour", "appearance": "Appearance"}
            observation_options = ["Not assessed", "Normal / characteristic", "Slight deviation", "Abnormal / objectionable"]
            for field in module["choices"]:
                values[field] = st.selectbox(choice_labels[field], observation_options, key=f"milk_{field}")
            values["consistency"] = st.selectbox("Consistency", ["Not assessed", "Normal", "Slightly altered", "Abnormal / clotted"], key="milk_consistency")

            st.markdown("### 5. Storage and handling conditions")
            d1, d2 = st.columns(2)
            storage_type = d1.selectbox("Storage condition", ["Not specified", "Ambient", "Refrigerated", "Chilled transport", "Frozen", "Processing-line hold"])
            storage_duration_hours = d2.number_input("Storage duration (hours)", min_value=0.0, step=0.5, value=0.0)
            d3, d4 = st.columns(2)
            milk_temp_raw = d3.text_input("Milk / product temperature (°C)", placeholder="Manual probe reading, if measured")
            storage_temp_raw = d4.text_input("Storage-unit temperature (°C)", placeholder="Manual reading, if available")
            d5, d6 = st.columns(2)
            storage_rh_raw = d5.text_input("Storage relative humidity (%)", placeholder="Optional")
            container = d6.selectbox("Container / package", ["Not specified", "Bulk tank", "Stainless steel can", "Glass bottle", "Plastic bottle", "Pouch", "Carton", "Other"])
            for field, raw in [("milk_temperature_c", milk_temp_raw), ("storage_temperature_c", storage_temp_raw), ("storage_humidity_pct", storage_rh_raw)]:
                if raw.strip():
                    try:
                        values[field] = float(raw)
                    except ValueError:
                        st.warning(f"{field.replace('_', ' ')}: enter a numeric value.")
                        values[field] = None
                else:
                    values[field] = None
            values["storage_type"] = storage_type
            values["storage_duration_hours"] = float(storage_duration_hours)
            values["container_type"] = container
            values["milk_category"] = milk_category
            values["milk_product_type"] = product_type
            values["supplier_source"] = source.strip()
            values["collection_location"] = collection_location.strip()
            values["sample_reference"] = sample_code.strip()

            st.markdown("### 6. Additional remarks")
            values["remarks"] = st.text_area("Observations / deviations / corrective action", placeholder="Record any unusual condition, test method, instrument ID or follow-up required.")
        else:
            product_type = st.text_input("Product / sample type *", placeholder="e.g. dahi, mango juice")
            st.markdown("**Manual laboratory readings**")
            columns = st.columns(2)
            for index, (field, label) in enumerate(module["fields"]):
                raw = columns[index % 2].text_input(label, key=f"{module_key}_{field}", placeholder="Enter measured value")
                if raw.strip():
                    try:
                        values[field] = float(raw)
                    except ValueError:
                        st.warning(f"{label}: enter a numeric value.")
                        values[field] = None
                else:
                    values[field] = None
            st.markdown("**Basic sensory / visual observations**")
            choice_labels = {
                "texture": "Texture", "syneresis": "Syneresis", "odour": "Odour",
                "ripeness": "Ripeness", "bruising": "Bruising", "appearance": "Appearance",
                "package_integrity": "Package integrity",
            }
            choices = ["Not assessed", "Acceptable", "Borderline", "Unacceptable"]
            for field in module["choices"]:
                values[field] = st.selectbox(choice_labels.get(field, field), choices, key=f"{module_key}_{field}")

        submitted = st.form_submit_button("Assess and save sample", type="primary")

   
    if submitted:
        if not batch_id.strip() or not str(product_type).strip():
            st.error("Batch ID and product/sample type are required.")
        else:
            # Attach the latest environmental readings separately.
            values["iot_snapshot"] = latest_sensor if latest_sensor else {}
            values["iot_snapshot_note"] = (
                "DHT11 readings are ambient conditions, not direct milk-core "
                "temperature. MQ2/MQ135 are raw sensor responses, not "
                "validated contaminant concentrations."
            )

            # Run the milk assessment.
            rule_grade, rule_explanation = classify_by_rules(
                module_key, values
            )

            ai_grade, ai_confidence, ai_error = predict_with_model(
                module_key, values
            )

            display_product = (
                f"{values['milk_category']} — {product_type}"
                if module_key == "milk"
                else str(product_type)
            )

            # Save exactly once, after successful validation.
            save_observation(
                batch_id.strip(),
                module_key,
                display_product,
                operator.strip(),
                "manual + latest IoT",
                values,
                rule_grade,
                ai_grade,
                ai_confidence
            )

            st.success("Sample assessment saved.")

            st.subheader("Assessment outcome")
            st.write(f"**{rule_grade}**")
            st.write(rule_explanation)

            if ai_error:
                st.info(ai_error)


        if batch_id.strip() and str(product_type).strip() and module_key == "milk":
            st.markdown("---")
            st.subheader("Milk Quality Assessment Report")

            # 1. Sample identification
            st.markdown("### 1. Sample identification")
            c1, c2, c3 = st.columns(3)
            c1.metric("Batch ID", batch_id.strip())
            c2.write(f"**Milk category:** {values.get('milk_category', '—')}")
            c3.write(f"**Milk type:** {product_type}")

            st.write(f"**Supplier:** {values.get('supplier_source') or 'Not provided'}")
            st.write(f"**Sample reference:** {values.get('sample_reference') or 'Not provided'}")

            # 2. Laboratory measurements
            st.markdown("### 2. Laboratory measurements")
            measurement_labels = {
                "fat_pct": "Fat (%)",
                "snf_pct": "SNF (%)",
                "total_sodium_mg_per_100g_snf": "Total sodium (mg per 100 g SNF)",
                "total_urea_ppm": "Total urea (ppm)",
                "ph": "pH",
                "titratable_acidity_pct_lactic_acid": "Titratable acidity (% lactic acid)",
                "density_kg_m3": "Density (kg/m³)"
            }

            measurement_cols = st.columns(3)
            for i, (field, label) in enumerate(measurement_labels.items()):
                value = values.get(field)
                measurement_cols[i % 3].metric(
                    label,
                    f"{value:g}" if value is not None else "Not measured"
                )

            # 3. Screening tests
            st.markdown("### 3. Stability and adulteration screening")
            screening_fields = [
                ("alcohol_test", "Alcohol stability"),
                ("clot_on_boiling_test", "Clot-on-boiling"),
                ("starch_screen", "Starch"),
                ("urea_screen", "Urea"),
                ("detergent_screen", "Detergent"),
                ("neutralizer_screen", "Neutralizer")
            ]

            for field, label in screening_fields:
                st.write(f"**{label}:** {values.get(field, 'Not tested')}")

            # 4. Sensory observations
            st.markdown("### 4. Sensory observations")
            for field in ["colour", "odour", "appearance", "consistency"]:
                st.write(f"**{field.replace('_', ' ').title()}:** {values.get(field, 'Not assessed')}")

            # 5. Storage and handling
            st.markdown("### 5. Storage and handling")
            st.write(f"**Storage condition:** {values.get('storage_type', 'Not specified')}")
            st.write(f"**Storage duration:** {values.get('storage_duration_hours', 0)} hours")
            st.write(f"**Milk temperature:** {values.get('milk_temperature_c') if values.get('milk_temperature_c') is not None else 'Not measured'}")
            st.write(f"**Storage temperature:** {values.get('storage_temperature_c') if values.get('storage_temperature_c') is not None else 'Not measured'}")
            st.write(f"**Container:** {values.get('container_type', 'Not specified')}")

            # 6. IoT snapshot
            st.markdown("### 6. Connected IoT readings")
            snapshot = values.get("iot_snapshot", {})

            if snapshot:
                iot_cols = st.columns(4)
                iot_labels = [
                    ("humidity_pct", "Ambient humidity", "%"),
                    ("temperature_c", "Ambient temperature", "°C"),
                    ("mq2_raw", "MQ2 raw", ""),
                    ("mq135_raw", "MQ135 raw", "")
                ]

                for i, (field, label, unit) in enumerate(iot_labels):
                    reading = snapshot.get(field)
                    iot_cols[i].metric(
                        label,
                        f"{reading:g} {unit}".strip() if reading is not None else "—"
                    )

                st.caption(values.get("iot_snapshot_note", ""))
            else:
                st.info("No IoT readings were available when this sample was submitted.")

            # 7. Assessment results
            st.markdown("### 7. Assessment results")

            r1, r2 = st.columns(2)
            r1.metric("Rule-based result", rule_grade)
            r2.metric(
                "AI model result",
                ai_grade if ai_grade is not None else "Not available"
            )

            st.info(rule_explanation)

            if ai_error:
                st.caption(ai_error)
            elif ai_confidence is not None:
                st.caption(f"Model confidence: {ai_confidence:.1%}. This is not a safety guarantee.")

            st.warning(
                "A/B/C grading remains disabled until verified, product-specific "
                "requirements and project quality bands are reviewed and configured. "
                "Screening tests alone do not establish milk safety."
            )

            # 8. Remarks
            st.markdown("### 8. Additional remarks")
            st.write(values.get("remarks") or "No additional remarks.")
            pdf_bytes = build_milk_pdf(
                values,
                batch_id.strip(),
                product_type,
                rule_grade,
                rule_explanation,
                ai_grade,
                ai_error,
                ai_confidence
            )

            st.download_button(
                label="Download Milk Assessment Report (PDF)",
                data=pdf_bytes,
                file_name=f"FOODIQ_{batch_id.strip().replace(' ', '_')}.pdf",
                mime="application/pdf",
                key="download_milk_pdf"
            )
        else:
            x, y = st.columns(2)
            x.metric("Rule-based result", rule_grade)
            y.metric("AI model result", ai_grade if ai_grade is not None else "Not available")
            st.info(rule_explanation)

            if ai_error:
                st.caption(ai_error)
            elif ai_confidence is not None:
                st.caption(f"Model confidence: {ai_confidence:.1%}. This is a model score, not a safety guarantee.")

        st.json(values)

elif page == "Data & history":
    st.subheader("Sample history and exports")
    history = read_history()

    if history.empty:
        st.info("No records saved yet. Submit a sample from one of the quality sections.")

    else:
        history_view = history.copy()

        # Extract supplier information from saved JSON payloads
        def get_supplier(payload):
            try:
                return json.loads(payload).get("supplier_source", "")
            except (ValueError, TypeError):
                return ""

        history_view["supplier"] = history_view["payload"].apply(get_supplier)

        history_view["record_date"] = pd.to_datetime(
            history_view["created_at"], errors="coerce"
        ).dt.date

        st.markdown("### Search and filter records")

        c1, c2 = st.columns(2)

        search_text = c1.text_input(
            "Search batch ID, supplier or product"
        )

        module_options = {
            "All categories": "All",
            "Milk quality": "milk",
            "Fermented products": "fermented",
            "Fruits and beverages": "fruit_beverage"
        }

        selected_module = c2.selectbox(
            "Food category",
            list(module_options.keys())
        )

        filtered = history_view.copy()

        if selected_module != "All categories":
            filtered = filtered[
                filtered["module"] == module_options[selected_module]
            ]

        if search_text.strip():
            search = search_text.strip().lower()

            searchable = (
                filtered["batch_id"].fillna("").astype(str).str.lower()
                + " "
                + filtered["product_type"].fillna("").astype(str).str.lower()
                + " "
                + filtered["supplier"].fillna("").astype(str).str.lower()
            )

            filtered = filtered[searchable.str.contains(search, regex=False)]

        valid_dates = history_view["record_date"].dropna()

        if not valid_dates.empty:
            date_range = st.date_input(
                "Filter by date range",
                value=(valid_dates.min(), valid_dates.max())
            )

            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range

                filtered = filtered[
                    filtered["record_date"].between(start_date, end_date)
                ]

        st.divider()

        st.markdown("### Filtered records")
        st.metric("Matching records", len(filtered))

        display_columns = [
            "id",
            "created_at",
            "batch_id",
            "module",
            "product_type",
            "supplier",
            "rule_result",
            "ai_result"
        ]

        st.dataframe(
            filtered[display_columns],
            use_container_width=True,
            hide_index=True
        )

        # CSV export
        csv_data = filtered.drop(
            columns=["payload"], errors="ignore"
        ).to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download filtered records (CSV)",
            data=csv_data,
            file_name="FOODIQ_filtered_history.csv",
            mime="text/csv"
        )

        st.divider()

        # Individual record inspection
        st.markdown("### Inspect an individual sample")

        if not filtered.empty:
            selected_id = st.selectbox(
                "Select sample record ID",
                filtered["id"].tolist()
            )

            selected = filtered[filtered["id"] == selected_id].iloc[0]

            st.write("**Batch ID:**", selected["batch_id"])
            st.write("**Product:**", selected["product_type"])
            st.write("**Date:**", selected["created_at"])
            st.write("**Rule result:**", selected["rule_result"])
            st.write("**AI result:**", selected["ai_result"])

            try:
                payload = json.loads(selected["payload"])
                st.markdown("#### Complete saved sample data")
                st.json(payload)
            except (ValueError, TypeError):
                st.error("Could not read the saved sample payload.")

        else:
            st.info("No records match the selected filters.")


elif page == "Expert Review & AI Data":
    st.subheader("Expert Review & AI Data Management")
    st.caption("Only documented expert assessments become training labels. Existing rule-based and AI results are not used as expert labels.")
    history = read_history()
    if history.empty:
        st.info("No saved observations are available for review.")
    else:
        reviews = read_expert_reviews()
        reviewed_ids = set(reviews["observation_id"].astype(int)) if not reviews.empty else set()
        st.metric("Awaiting expert review", int((~history["id"].astype(int).isin(reviewed_ids)).sum()))
        options = history.copy()
        options["display"] = options.apply(
            lambda r: f"#{int(r['id'])} · {r['batch_id']} · {r['module']} · {r['product_type']}", axis=1)
        selected = st.selectbox("Select saved sample", options["display"].tolist())
        sample = options[options["display"] == selected].iloc[0]
        payload = json.loads(sample["payload"] or "{}")
        with st.expander("Inspect original sample data", expanded=True):
            st.write({"Observation ID": int(sample["id"]), "Batch ID": sample["batch_id"],
                      "Module": sample["module"], "Product": sample["product_type"],
                      "Recorded": sample["created_at"], "Rule result": sample["rule_result"],
                      "AI result": sample["ai_result"]})
            st.json(payload)
        prior_df = reviews[reviews["observation_id"] == int(sample["id"])] if not reviews.empty else pd.DataFrame()
        prior = prior_df.iloc[0] if not prior_df.empty else None
        grades = ["A", "B", "C", "HOLD", "INSUFFICIENT DATA"]
        with st.form("expert_review_form"):
            st.markdown("### Expert assessment")
            st.caption("A saved review is not eligible for the AI training CSV until the reviewer confirms that its supporting evidence has been checked.")
            grade = st.selectbox("Expert-assigned outcome", grades,
                index=grades.index(prior["expert_grade"]) if prior is not None and prior["expert_grade"] in grades else 0)
            reviewer = st.text_input("Reviewer name *", value=str(prior["reviewed_by"]) if prior is not None else "")
            qualification = st.text_input("Reviewer qualification / role *",
                value=str(prior["reviewer_qualification"]) if prior is not None else "")
            reference_standard = st.text_input("Applicable standard / protocol *",
                value=str(prior.get("reference_standard", "") or "") if prior is not None else "",
                help="Enter the exact standard, specification, SOP or sensory rubric used. Do not claim regulatory compliance without verification.")
            measurement_methods = st.text_area("Laboratory methods and evidence checked *",
                value=str(prior.get("measurement_methods", "") or "") if prior is not None else "",
                help="List the actual methods used and identify which results were verified.")
            basis = st.text_area("Assessment basis *",
                value=str(prior["label_basis"]) if prior is not None else "",
                help="Explain how the evidence supports the selected outcome.")
            grade_rationale = st.text_area("Reason for assigning this grade *",
                value=str(prior.get("grade_rationale", "") or "") if prior is not None else "")
            safety_concerns = st.text_area("Safety / compliance concerns",
                value=str(prior.get("safety_concerns", "") or "") if prior is not None else "",
                help="Record concerns, failed screens, missing tests or reasons for HOLD. Enter 'None identified in the tests performed' only when justified.")
            evidence_verified = st.checkbox(
                "I have checked the underlying sample data and supporting laboratory evidence; this review is suitable for labelled-dataset consideration.",
                 value=(
                    bool(prior.get("evidence_verified", 0))
                    if prior is not None and grade != "INSUFFICIENT DATA"
                    else False
                 ),
                disabled=(grade == "INSUFFICIENT DATA")
            )
            review_date = st.date_input("Review date",
                value=pd.to_datetime(prior["review_date"]).date() if prior is not None and pd.notna(prior["review_date"]) else datetime.now().date())
            notes = st.text_area("Additional review notes", value=str(prior["review_notes"]) if prior is not None else "")
            save_review = st.form_submit_button("Save expert review", type="primary")
        if save_review:
            required_text = [reviewer, qualification, reference_standard, measurement_methods, basis, grade_rationale]
            if not all(str(value).strip() for value in required_text):
                st.error("Complete all required reviewer, protocol, methods and grade-rationale fields.")
            else:
                save_expert_review(int(sample["id"]), grade, reviewer, qualification, basis, review_date, notes,
                    evidence_verified, reference_standard, measurement_methods, grade_rationale, safety_concerns)
                st.success("Expert review saved. It will enter the labelled training dataset only if evidence verification is checked.")
                st.rerun()

    st.divider()
    st.markdown("### Labelled dataset management")
    st.caption("Export reviewed records using the existing module-specific template columns.")
    labels = {"milk":"Milk quality"}
    module_key = "milk"
    st.caption("FOODIQ is currently configured for the Milk Quality module only.")
    try:
        dataset = build_labelled_dataset(module_key)
        issues = validate_labelled_dataset(dataset)
        st.metric("Expert-labelled records", len(dataset))
        for issue in issues:
            st.warning(issue)
        if not issues:
            st.success("Dataset validation passed.")
        st.dataframe(dataset, use_container_width=True, hide_index=True)
        st.download_button("Download labelled training CSV", dataset.to_csv(index=False).encode("utf-8"),
            f"{module_key}_training_template.csv", "text/csv", key=f"expert_csv_{module_key}")
        if st.button("Update project training CSV", type="primary", key=f"write_csv_{module_key}"):
            if issues:
                st.error("Dataset was not written because validation found issues.")
            else:
                filename = {"milk":"milk_training_template.csv",
                            "fermented":"fermented_training_template.csv",
                            "fruit_beverage":"fruit_beverage_training_template.csv"}[module_key]
                target = APP_DIR / "ai_datasets" / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                dataset.to_csv(target, index=False)
                st.success(f"Updated {filename} with {len(dataset)} expert-reviewed records.")
    except Exception as exc:
        st.error(f"Could not build this dataset: {exc}")
    st.info("Expert labels are not generated automatically. A saved review does not itself train a model; model training still requires sufficient genuine labels and independent evaluation.")

elif page == "Standards and AI setup":
    st.subheader("Standards and AI setup")
    st.caption("FOODIQ development scope: Milk Quality only. Regulatory rules remain disabled until independently checked and approved.")
    st.info("Initial validation scope: raw cow milk and raw buffalo milk. Composition limits are stored as reference checks, not activated as regulatory decisions. Confirm the current Gazette text, product definition, sampling point and analytical method before enabling them.")

    rules = load_rules()
    category_labels = {"milk": "Milk quality"}
    selected_key = st.selectbox(
        "Food category to configure",
        list(category_labels.keys()),
        format_func=lambda key: category_labels[key],
    )
    current_config = rules.get(selected_key, {
        "enabled": False, "source": "", "reviewed_by": "", "criteria": {}, "hard_limits": []
    })

    st.markdown("### Standards configuration")
    st.write("Edit the selected category's configuration below. Keep mandatory compliance limits (`hard_limits`) separate from project-defined quality grades (`criteria`).")
    config_text = st.text_area(
        "Category configuration (JSON)",
        value=json.dumps(current_config, indent=2, ensure_ascii=False),
        height=330,
        key=f"rules_editor_{selected_key}",
        help="Only enter limits that have been checked against the applicable current regulation or an explicitly documented project protocol.",
    )
    if st.button("Validate and save this category", type="primary", key="save_rules_" + selected_key):
        try:
            proposed = json.loads(config_text)
            required_keys = {"enabled", "source", "reviewed_by", "criteria", "hard_limits"}
            missing_keys = required_keys - set(proposed)
            if missing_keys:
                st.error("Missing required keys: " + ", ".join(sorted(missing_keys)))
            elif not isinstance(proposed["enabled"], bool):
                st.error("'enabled' must be true or false.")
            elif not isinstance(proposed["source"], str) or not isinstance(proposed["reviewed_by"], str):
                st.error("'source' and 'reviewed_by' must be text values.")
            elif not isinstance(proposed["criteria"], dict) or not isinstance(proposed["hard_limits"], list):
                st.error("'criteria' must be a JSON object and 'hard_limits' must be a JSON list.")
            elif proposed["enabled"] and (not proposed["source"].strip() or not proposed["reviewed_by"].strip()):
                st.error("Before enabling rules, provide the exact source and the reviewer.")
            elif proposed["enabled"] and not proposed["criteria"] and not proposed["hard_limits"]:
                st.error("Rules cannot be enabled while both criteria and hard_limits are empty.")
            else:
                rules[selected_key] = proposed
                RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                st.success(f"Saved configuration for {category_labels[selected_key]}. Other categories were preserved.")
                st.rerun()
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
        except OSError as exc:
            st.error(f"Could not save quality_rules.json: {exc}")

    st.info("Keep 'enabled' set to false until the source, units, limits and reviewer have been verified. A/B/C bands are project-defined and are not universal FSSAI grades.")

    st.divider()
    st.markdown("### AI model status")
    model_files = {"milk": "fssai_decision_tree_demo.joblib"}
    model_cols = st.columns(len(model_files))
    for col, (module_key, filename) in zip(model_cols, model_files.items()):
        model_path = MODEL_DIR / filename
        with col:
            st.markdown(f"**{category_labels[module_key]}**")
            if not model_path.exists():
                st.warning("Not trained / model file not found")
            else:
                try:
                    artifact = joblib.load(model_path)
                    st.success("Model file found")
                    if isinstance(artifact, dict):
                        features = artifact.get("features", [])
                        st.caption(f"Features recorded: {len(features)}")
                        metrics = artifact.get("metrics")
                        if isinstance(metrics, dict) and metrics:
                            st.json(metrics)
                        else:
                            st.caption("No evaluation metrics stored in this model artifact.")
                    else:
                        st.caption("Model artifact exists; metadata is not in the expected dictionary format.")
                except Exception as exc:
                    st.error(f"Model file could not be loaded: {exc}")

    st.markdown("### AI training requirements")
    st.write("Train each category using real laboratory observations with verified labels. Keep separate training and test batches, and evaluate with accuracy, precision, recall, F1-score and a confusion matrix. Do not use the live MQ2/MQ135 raw values as proof of milk adulteration without experimental validation.")
    st.caption("Configured model path: models/fssai_decision_tree_demo.joblib. The FSSAI rule screen remains separate from model output.")

st.divider()
st.caption("FOODIQ is a development prototype. It does not replace accredited laboratory testing, regulatory review, or a food-safety release decision.")
