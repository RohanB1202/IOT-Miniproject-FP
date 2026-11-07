# FOODIQ starter project

A Streamlit prototype for an IoT-enabled food quality monitoring and sample-recording system.

## Files
- `app.py`: Streamlit website with dashboard, three product modules, manual entry, history and CSV export.
- `quality_rules.json`: deliberately disabled rule configuration. Add only verified, product-specific limits.
- `train_model_colab.py`: baseline Colab training workflow. Train one model per module on real labelled data.
- `quality_dataset_template.csv`: dataset column template; it contains no fabricated observations.
- `requirements.txt`: Python dependencies.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `python -m venv .venv` and activate the environment.
4. Run `pip install -r requirements.txt`.
5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and enter the ThingSpeak channel ID and Read API Key.
6. Run `streamlit run app.py`.

If ThingSpeak is not configured, the manual entry and history portions still work.

## ThingSpeak field mapping
The app currently assumes:
- Field 1 = humidity (%)
- Field 2 = temperature (°C)
- Field 3 = MQ2 raw ADC value
- Field 4 = MQ135 raw ADC value

Change `field_map` in `fetch_thingspeak()` if your ThingSpeak channel uses another mapping. Confirm that the ESP8266 (or a computer gateway) is actually uploading values; the uploaded internship report's Arduino sketch outputs serial data, so the Wi-Fi upload bridge/firmware must be checked.

## Configure standards carefully
The app will not grade a product until its section is enabled in `quality_rules.json`. The structure for each criterion is:

```json
"fat_pct": {
  "grade_a": {"min": 3.0, "max": 4.0},
  "grade_b": {"min": 2.5, "max": 4.5}
}
```

The numbers above are only a syntax example, NOT FSSAI limits and must not be used as a real standard. Grade B ranges should include the Grade A band. Add exact hard limits separately under `hard_limits`, with an `allowed` min/max range and a plain-language `reason`. Keep regulatory compliance checks separate from project-defined quality grades. Record source, amendment/effective date, units and reviewer.

## Train AI in Colab
1. Collect actual QC/lab measurements and final labels from qualified review.
2. Add rows to a copy of `quality_dataset_template.csv` and save it as `quality_dataset.csv`.
3. Open Google Colab, upload `train_model_colab.py` and your CSV, and run the script.
4. Set `MODULE_TO_TRAIN` and the feature list for that product category.
5. Review the batch-independent test metrics and confusion matrix. Do not deploy a model that has not been validated on independent batches.
6. Download the `.joblib` artifact and place it in `models/` using the expected filename.
7. Deploy/update the Streamlit app.

## Prototype limitations
- SQLite is suitable for a single-user/local prototype. For a shared deployed app, move observations to a managed database such as Supabase/Postgres.
- Streamlit Community Cloud does not provide direct access to your local Arduino USB port. Use ThingSpeak as the cloud relay, or run the app locally with a serial gateway.
- MQ2/MQ135 raw counts are sensor signals, not validated concentrations of a named spoilage gas.
- Model output is decision support only. It does not establish product safety or replace accredited testing.
