import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import requests
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "foodiq.db"
RULES_PATH = APP_DIR / "quality_rules.json"
MODEL_DIR = APP_DIR / "models"

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


def secret_value(section, key, env_name=None, default=""):
    try:
        value = st.secrets.get(section, {}).get(key, default)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(env_name or key.upper(), default)


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


def classify_by_rules(module_key, values):
    config = load_rules().get(module_key, {})
    if not config.get("enabled", False):
        return "Not configured", "Add reviewed, product-specific rules to quality_rules.json before assigning grades."

    # Mandatory safety checks are independent of the A/B/C quality grade.
    for check in config.get("hard_limits", []):
        field = check.get("field")
        if field in values and values[field] is not None:
            if not in_range(values[field], check.get("allowed", {})):
                return "HOLD", check.get("reason", "A mandatory safety/compliance limit was not met.")

    criteria = config.get("criteria", {})
    if not criteria:
        return "Insufficient rules", "No quality criteria have been configured."

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
    if not model_path.exists():
        return None, None, "No trained model found for this section."
    try:
        artifact = joblib.load(model_path)
        model = artifact["model"]
        features = artifact["features"]
        row = {name: values.get(name) for name in features}
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
    page = st.radio("Open section", ["Dashboard", *MODULES.keys(), "Data & history", "Standards and AI setup"])
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
                product_type = c2.selectbox("Processed milk type *", ["Pasteurised milk", "Toned milk", "Double toned milk", "Standardised milk", "Full cream milk", "Homogenised milk", "UHT milk", "Other processed milk"])
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
            # Attach the latest environmental readings as a separate, timestamped snapshot.
            values["iot_snapshot"] = latest_sensor if latest_sensor else {}
            values["iot_snapshot_note"] = "DHT11 readings are ambient conditions, not direct milk-core temperature. MQ2/MQ135 are raw sensor responses, not validated contaminant concentrations."
            rule_grade, rule_explanation = classify_by_rules(module_key, values)
            ai_grade, ai_confidence, ai_error = predict_with_model(module_key, values)
            display_product = f"{values['milk_category']} — {product_type}" if module_key == "milk" else str(product_type)
            save_observation(batch_id.strip(), module_key, display_product, operator.strip(), "manual + latest IoT", values, rule_grade, ai_grade, ai_confidence)
            st.success("Sample assessment saved.")
            x, y = st.columns(2)
            x.metric("Rule-based result", rule_grade)
            y.metric("AI model result", ai_grade if ai_grade is not None else "Not available")
            st.info(rule_explanation)
            if ai_error:
                st.caption(ai_error)
            elif ai_confidence is not None:
                st.caption(f"Model confidence: {ai_confidence:.1%}. This is a model score, not a safety guarantee.")
            if module_key == "milk":
                st.warning("A/B/C grading remains disabled until verified, product-specific FSSAI requirements and separately defined project quality bands are reviewed and configured. Screening tests marked Pass do not independently establish milk safety.")
            st.json(values)

elif page == "Data & history":
    st.subheader("Sample history and exports")
    history = read_history()
    if history.empty:
        st.info("No records saved yet. Submit a sample from one of the quality sections.")
    else:
        st.dataframe(history.drop(columns=["payload"]), use_container_width=True)
        st.download_button("Download observations CSV", history.to_csv(index=False).encode("utf-8"), "foodiq_observations.csv", "text/csv")
        with st.expander("Inspect a saved sample"):
            selected_id = st.number_input("Observation ID", min_value=1, step=1)
            selected = history[history["id"] == selected_id]
            if not selected.empty:
                st.json(json.loads(selected.iloc[0]["payload"]))

elif page == "Standards and AI setup":
    st.subheader("Standards and AI setup")
    st.caption("Manage reviewed standards and inspect AI model readiness. No regulatory limits are pre-filled or assumed.")

    rules = load_rules()
    category_labels = {
        "milk": "Milk quality",
        "fermented": "Fermented products",
        "fruit_beverage": "Fruits and beverages",
    }
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
    model_files = {
        "milk": "milk_model.joblib",
        "fermented": "fermented_model.joblib",
        "fruit_beverage": "fruit_beverage_model.joblib",
    }
    model_cols = st.columns(3)
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
    st.caption("Expected model paths: models/milk_model.joblib, models/fermented_model.joblib and models/fruit_beverage_model.joblib.")

st.divider()
st.caption("FOODIQ is a development prototype. It does not replace accredited laboratory testing, regulatory review, or a food-safety release decision.")
