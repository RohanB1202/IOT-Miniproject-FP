from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE

OUT = r"C:\Users\ASUS\OneDrive\Documents\foodiq_starter_v2\FOODIQ_Integrated_IoT_and_Milk_Quality_Monitoring_Project_Report.docx"

NAVY = "17365D"
BLUE = "DCE6F1"
PALE = "F4F7FA"
GRID = "D9D9D9"
BLACK = "000000"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color=GRID):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=90, start=105, bottom=90, end=105):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    elem = OxmlElement("w:tblHeader")
    elem.set(qn("w:val"), "true")
    tr_pr.append(elem)


def set_column_width(cell, inches):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(inches * 1440)))
    tc_w.set(qn("w:type"), "dxa")


def set_run_font(run, size=None, bold=None, italic=None, color=BLACK):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    set_run_font(run, 9)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def add_para(doc, text="", style=None, bold_lead=None, italic=False, align=None, space_after=6):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        set_run_font(r, 11, bold=True)
        r2 = p.add_run(text[len(bold_lead):])
        set_run_font(r2, 11, italic=italic)
    else:
        r = p.add_run(text)
        set_run_font(r, 11, italic=italic)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.25
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    r = p.add_run(text)
    set_run_font(r, 15 if level == 1 else 12, bold=True)
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(7 if level == 1 else 5)
    p.paragraph_format.keep_with_next = True
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    set_run_font(r, 11)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    return p


def add_table(doc, headers, rows, widths=None, font_size=9.5):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, title in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = ""
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if widths: set_column_width(cell, widths[i])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title)
        set_run_font(r, font_size, bold=True, color="FFFFFF")
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            cell.text = ""
            set_cell_shading(cell, PALE if ridx % 2 else "FFFFFF")
            set_cell_border(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths: set_column_width(cell, widths[i])
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.08
            r = p.add_run(str(value))
            set_run_font(r, font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
sec.left_margin = sec.right_margin = Inches(0.9)
sec.top_margin, sec.bottom_margin = Inches(0.8), Inches(0.75)
sec.header_distance, sec.footer_distance = Inches(0.35), Inches(0.35)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Times New Roman"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
normal.font.size = Pt(11)
for name, size in (("Title", 22), ("Heading 1", 15), ("Heading 2", 12)):
    st = styles[name]
    st.font.name = "Times New Roman"
    st._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    st._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)

footer = sec.footer
add_page_number(footer.paragraphs[0])

# Cover
for _ in range(3): doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("FOODIQ")
set_run_font(r, 27, bold=True, color=NAVY)
p.paragraph_format.space_after = Pt(10)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Integrated IoT and Milk Quality Monitoring Project Report")
set_run_font(r, 19, bold=True)
p.paragraph_format.space_after = Pt(20)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("End to end project documentation covering the IoT sensor module, ThingSpeak cloud relay, Streamlit web application, data management, FSSAI reference screening and decision tree evaluation")
set_run_font(r, 12, italic=True)
p.paragraph_format.space_after = Pt(34)
add_table(doc, ["Project area", "Implemented scope"], [
    ("IoT monitoring", "Live temperature, humidity, MQ2 and MQ135 readings through ThingSpeak"),
    ("Web application", "Streamlit dashboard, milk assessment, history, expert review and report export"),
    ("Data and AI", "SQLite records, provisioned MySQL storage, FSSAI reference dataset and decision tree evaluation"),
], widths=[1.7, 4.7], font_size=10)
for _ in range(3): doc.add_paragraph()
for text, size, bold in [
    ("Prepared by", 11, False),
    ("Rohan Biju  URK23FP2013", 13, True),
    ("Bachelor of Technology  Food Processing and Engineering", 11, False),
    ("Karunya Institute of Technology and Sciences", 11, False),
    ("November 2026", 11, False),
]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); set_run_font(r, size, bold=bold)
    p.paragraph_format.space_after = Pt(5)
doc.add_page_break()

# Abstract and contents
add_heading(doc, "Abstract", 1)
add_para(doc, "FOODIQ is an integrated prototype for food-quality record keeping and environmental monitoring. It extends a previously developed Arduino Nano sensor module into a complete software workflow: the module measures temperature, humidity, MQ2 and MQ135 signals; readings are relayed to ThingSpeak; a Streamlit application presents live values and trends; laboratory and screening observations can be recorded; and structured data can be reviewed for quality decisions.")
add_para(doc, "The current implemented scope focuses on milk quality. The web application captures product information, compositional measurements, selected stability and adulteration screens, sensory observations, storage conditions and an IoT snapshot. It maintains an auditable observation history in SQLite, supports expert review, and can generate a sample PDF report. A local MySQL server was configured and loaded with the project test dataset as a separate storage demonstration.")
add_para(doc, "The project also includes a 1,200-row FSSAI-reference milk-composition test dataset and a decision tree classifier. The model is integrated in the app as decision support and achieved 95.42% held-out accuracy on its rule-derived test labels. It is not a regulatory compliance engine or substitute for accredited laboratory testing. The report documents the completed work, its verification, and the next steps needed for real-world deployment.")
add_para(doc, "Keywords: Internet of Things, food quality monitoring, milk quality, ThingSpeak, Streamlit, FSSAI reference screening, decision tree classifier", italic=True)

add_heading(doc, "Contents", 1)
toc = [
    ("1", "Project introduction and objectives"), ("2", "Development journey and system architecture"),
    ("3", "IoT sensing module and ThingSpeak integration"), ("4", "FOODIQ web application"),
    ("5", "Data management and quality workflow"), ("6", "FSSAI reference dataset and decision tree model"),
    ("7", "Verification results and current status"), ("8", "Limitations and future development"),
    ("9", "Conclusion"), ("Appendix A", "Project file inventory"), ("Appendix B", "FSSAI reference categories used for the test dataset")
]
add_table(doc, ["Section", "Title"], toc, widths=[1.1, 5.3], font_size=10)
doc.add_page_break()

# Chapter 1
add_heading(doc, "1 Project introduction and objectives", 1)
add_heading(doc, "1.1 Background", 2)
add_para(doc, "Food quality management benefits from two complementary views: environmental conditions around a food product and the product-level observations made during inspection or laboratory analysis. The earlier IoT module supplied the first view by measuring ambient temperature, humidity and raw gas-sensor responses. FOODIQ was developed to connect that live monitoring capability with a usable web interface for recording, reviewing and interpreting milk-quality observations.")
add_para(doc, "The project is a prototype for learning and demonstration. It does not claim that MQ2 or MQ135 raw values identify a specific spoilage compound, nor does it infer legal compliance from a single sensor or prediction. Instead, it establishes a traceable path from sensor reading to cloud record, dashboard display, sample entry, review and model-supported composition screening.")
add_heading(doc, "1.2 Objectives", 2)
for x in [
    "Reuse the existing IoT food-spoilage sensor module to provide live temperature, humidity, MQ2 and MQ135 readings.",
    "Receive and visualize those readings through a ThingSpeak cloud channel in a locally running Streamlit website.",
    "Create a milk-quality workflow that records composition, screening observations, sensory notes, storage conditions and IoT context in one place.",
    "Use FSSAI reference values carefully for composition screening while preserving the distinction between a reference check, expert review and legal compliance.",
    "Prepare a structured test dataset, evaluate a transparent decision tree classifier and integrate it as a clearly limited decision-support feature.",
    "Establish local data storage for the prototype and provision MySQL for a future shared database path."
]: add_bullet(doc, x)

add_heading(doc, "1.3 Project outcomes", 2)
add_table(doc, ["Workstream", "Outcome completed"], [
    ("Embedded sensing", "Arduino Nano based module reused with DHT11, MQ2 and MQ135 sensing, local LCD/LED/buzzer feedback and serial packets."),
    ("Cloud relay", "ThingSpeak field mapping established for humidity, temperature, MQ2 and MQ135; the app reads recent channel entries."),
    ("Application", "Milk-focused Streamlit interface with dashboard, entry form, history, CSV export, expert review and PDF reporting."),
    ("Quality framework", "Milk reference checks are deliberately disabled pending independent review; screening data are kept separate from composition grades."),
    ("Model", "Decision tree trained and tested on the 1,200-row rule-derived test dataset, then exposed to the milk workflow."),
    ("Storage", "SQLite remains the active application store; local MySQL was installed, configured and loaded with the demonstration milk assessment table."),
], widths=[1.55, 4.85], font_size=9.3)

# Chapter 2
add_heading(doc, "2 Development journey and system architecture", 1)
add_para(doc, "The work progressed from a standalone environmental-monitoring prototype to an integrated food-quality software system. The first stage established reliable multi-sensor acquisition and local feedback. The second stage moved readings to ThingSpeak for remote visibility. The third stage created FOODIQ as the web interface and record system. The final stages added standards-aware data design, local database setup, a test dataset and a transparent classification model.")
add_heading(doc, "2.1 End to end flow", 2)
add_table(doc, ["Stage", "Input", "Processing", "Result"], [
    ("1  Sense", "DHT11, MQ2 and MQ135", "Arduino Nano reads humidity, temperature and raw sensor values", "Serial packet: humidity, temperature, MQ2, MQ135"),
    ("2  Relay", "Serial packet or Wi Fi upload", "ESP8266 pathway or optional USB serial bridge forwards readings", "ThingSpeak channel entries"),
    ("3  Monitor", "ThingSpeak recent entries", "Streamlit fetches, maps and displays live values and trends", "Dashboard metrics and charts"),
    ("4  Assess", "Milk sample inputs and IoT snapshot", "Composition, screens, notes and storage conditions are recorded", "Observation history and PDF report"),
    ("5  Review", "Observation evidence", "Expert labels and review notes can be linked to observations", "Verified training evidence"),
    ("6  Learn", "Test dataset or future verified labels", "Decision tree evaluates composition-screen result patterns", "Decision-support prediction with limitations"),
], widths=[0.8, 1.45, 2.3, 1.85], font_size=8.8)
add_heading(doc, "2.2 Implementation milestones", 2)
for x in [
    "Built and tested the IoT spoilage-sensor module with an Arduino Nano, DHT11, MQ2 and MQ135 sensors, local display and alert outputs.",
    "Published live environmental values to ThingSpeak and confirmed the four-field mapping used by FOODIQ.",
    "Developed the Streamlit application and narrowed the active interface to the milk-quality workflow.",
    "Added reliable local observation history, expert-review support, CSV export and sample PDF report generation.",
    "Reviewed the relevant milk-composition reference values and deliberately prevented unsupported A/B/C grading or automatic regulatory claims.",
    "Generated a structured 1,200-row test dataset, provided an Excel-friendly CSV version and loaded the records into MySQL.",
    "Trained, evaluated and integrated a decision tree composition-screen classifier."
]: add_bullet(doc, x)

# Chapter 3
add_heading(doc, "3 IoT sensing module and ThingSpeak integration", 1)
add_heading(doc, "3.1 Hardware module", 2)
add_para(doc, "The same physical module documented in the earlier IoT project was retained for FOODIQ. Its Arduino Nano is the local controller. The DHT11 provides temperature and relative-humidity readings. MQ2 and MQ135 provide raw analogue responses used as environmental gas and air-quality indicators. A 16 x 2 LCD, LEDs and buzzer offer local feedback, while serial output supplies the values needed for cloud relay.")
add_table(doc, ["Component", "Role in the module", "How FOODIQ uses it"], [
    ("Arduino Nano", "Reads sensors, controls display/alerts and formats serial output.", "Source of the structured four-value packet."),
    ("DHT11", "Measures ambient temperature and humidity.", "Live dashboard metrics and time-series display."),
    ("MQ2", "Provides a raw response to combustible-gas related environmental changes.", "Shown as a raw ADC signal, not a calibrated concentration."),
    ("MQ135", "Provides a raw air-quality / gas-sensor response.", "Shown as a raw ADC signal, not a validated named-gas concentration."),
    ("LCD, LEDs and buzzer", "Show readings and provide local threshold feedback.", "Local prototype feedback; not required for the web dashboard."),
    ("ESP8266 or USB gateway", "Transfers formatted values to the cloud.", "Connects the module to the ThingSpeak channel."),
], widths=[1.2, 2.65, 2.6], font_size=9.1)
add_heading(doc, "3.2 Packet and field mapping", 2)
add_para(doc, "The firmware produces a serial message in the sequence humidity, temperature, MQ2, MQ135, terminated by a hash character. The optional Python bridge listens on the Arduino serial port, validates the four fields and posts them to ThingSpeak with a minimum 20-second update interval. The bridge is not used when the ESP8266 already uploads the same data, preventing duplicate entries.")
add_table(doc, ["ThingSpeak field", "Mapped value", "Unit or interpretation"], [
    ("Field 1", "Humidity", "Percent relative humidity"),
    ("Field 2", "Temperature", "Degrees Celsius"),
    ("Field 3", "MQ2", "Raw analogue / ADC sensor value"),
    ("Field 4", "MQ135", "Raw analogue / ADC sensor value"),
], widths=[1.5, 2.0, 2.95], font_size=10)
add_heading(doc, "3.3 Cloud to application connection", 2)
add_para(doc, "FOODIQ reads the latest ThingSpeak channel entries through credentials stored outside the source code, in Streamlit secrets or environment variables. The dashboard can continue to support manual entry and local history if the cloud channel is unavailable. This design keeps the core record-keeping workflow usable without exposing the channel credential or requiring direct USB access from a cloud-hosted app.")
add_para(doc, "The readings are useful as contextual storage-environment evidence. Their strongest current purpose is trend monitoring and a time-stamped snapshot accompanying a milk sample record. Sensor values must be calibrated and validated against appropriate reference instruments before being used as product-specific spoilage or safety thresholds.")

# Chapter 4
add_heading(doc, "4 FOODIQ web application", 1)
add_heading(doc, "4.1 Application design", 2)
add_para(doc, "FOODIQ is built in Python using Streamlit. It is intended as a local prototype interface that combines live monitoring with milk-quality record management. The application runs from app.py and stores working observation records in the project SQLite database. It can be launched locally with the Python environment supplied for the project.")
add_table(doc, ["Page", "Implemented functions"], [
    ("Dashboard", "Fetches recent ThingSpeak entries; displays current humidity, temperature, MQ2 and MQ135 values; shows trend charts and a recent-data table."),
    ("Milk Quality", "Captures milk category and product type, composition values, screening outcomes, sensory observations, storage conditions and a live IoT snapshot."),
    ("Data and History", "Lists saved observations, supports filtering and CSV export for downstream use."),
    ("Expert Review and AI Data", "Associates observations with qualified-review labels and prepares verified-label data for a future real training dataset."),
    ("Standards and AI Setup", "Displays the controlled milk rules configuration and the available decision-support model status."),
], widths=[1.45, 5.0], font_size=9.3)
add_heading(doc, "4.2 Milk sample record", 2)
add_para(doc, "The milk-entry form was designed so that a single observation contains both analytical and operational context. The key composition inputs are fat percentage, solids-not-fat, pH, titratable acidity, density, total sodium and total urea. The form also records alcohol and clot-on-boiling stability screens, starch, urea, detergent and neutralizer screens, sensory observations and storage details. The app can attach the latest IoT values to the same record and create a concise PDF report for the entered sample.")
add_heading(doc, "4.3 Expert evidence path", 2)
add_para(doc, "Model development needs trustworthy ground truth. FOODIQ therefore retains an expert-review path rather than assuming that a user-entered outcome is a final quality label. Observation and review records are joined only when a qualified review is available. The standard training scripts expect real labelled data, at least 30 labels and at least five examples per class before a general model is trained. At the current project stage, the real training templates are structurally valid but contain no eligible expert labels.")

# Chapter 5
add_heading(doc, "5 Data management and quality workflow", 1)
add_heading(doc, "5.1 Local data storage", 2)
add_para(doc, "SQLite is the active storage engine used by the Streamlit application. It contains the observation and expert-review structures needed for the local prototype. The design keeps the app simple to run on one computer while preserving sample history. A MySQL 8.0 server was also installed locally, placed on the command path, configured to start automatically and prepared with a FOODIQ database and a restricted application account. The 1,200-row test dataset was loaded into the MySQL milk_quality_assessments table.")
add_para(doc, "The Streamlit application has not yet been migrated to read and write MySQL; SQLite remains the operational source of application history. This separation is intentional in the report because it distinguishes completed MySQL provisioning and data loading from a future production database migration.")
add_heading(doc, "5.2 Quality and standards safeguards", 2)
add_para(doc, "The project uses FSSAI milk-composition values as reference material for the test dataset and controlled screening logic. The active rules configuration is disabled, and product grading is not automatically activated. This prevents the application from presenting unreviewed values as a legal or final quality grade. Composition checks are also kept separate from adulteration and stability screening outcomes.")
add_table(doc, ["Decision type", "Current FOODIQ treatment", "Meaning"], [
    ("Composition reference screen", "Available only as controlled reference / model-support context.", "Flags whether entered values align with the selected reference thresholds."),
    ("Screening test", "Recorded independently.", "A positive or failed screen requires confirmatory review; it is not averaged into a grade."),
    ("Expert review", "Supported through dedicated review records.", "Provides the evidence needed for verified training labels and final review workflow."),
    ("Regulatory compliance", "Not automatically claimed.", "Requires current legal instrument, product scope, method and qualified review."),
], widths=[1.6, 2.6, 2.15], font_size=9.0)
add_para(doc, "The controlled configuration records reference minima for raw cow and buffalo milk and keeps the grade-system labels disabled. It specifically avoids inventing A/B/C grade bands. This is important because a reference compendium must be checked against current official notifications, the applicable product definition, measurement method and amendment status before it can support compliance decisions.")

# Chapter 6
add_heading(doc, "6 FSSAI reference dataset and decision tree model", 1)
add_heading(doc, "6.1 Test dataset design", 2)
add_para(doc, "A structured milk-composition test dataset was created to exercise the screening and model pipeline. It contains 1,200 records across ten milk classes, with 120 records per class. It includes composition values, total sodium, total urea, pH, acidity, density and storage-related fields, along with the reference minima or maxima used to assess the sample. The output is available in ordinary CSV and Excel-friendly CSV form so that spreadsheet software separates the fields correctly.")
add_table(doc, ["Dataset characteristic", "Value"], [
    ("Records", "1,200"), ("Milk classes", "10; 120 records per class"), ("Screening outcomes", "840 PASS and 360 HOLD"),
    ("Core features", "Fat, SNF, sodium, urea and milk class"),
    ("Reference categories", "Cow, Buffalo, Goat/Sheep, Camel, Mixed, Standardised, Toned, Double Toned, Skimmed and Full Cream"),
    ("Files", "fssai_milk_quality_dataset.csv and fssai_milk_quality_dataset_excel.csv"),
], widths=[2.0, 4.35], font_size=9.3)
add_para(doc, "This is a rule-derived test dataset designed for development, interface testing and model evaluation. It is not a replacement for real laboratory observations, and it must not be represented as a field or accredited-laboratory dataset. The dataset purpose is retained in the project documentation even though the user-facing spreadsheet columns are clean and tabular.")
add_heading(doc, "6.2 Decision tree implementation", 2)
add_para(doc, "A DecisionTreeClassifier was selected because it is transparent, fast to run locally and easy to inspect. The model predicts the test dataset’s composition-screen result from fat percentage, SNF percentage, total sodium, total urea and milk class. It deliberately does not use the reference-limit columns or failure-reason text as model features, avoiding direct leakage of the rule result into the prediction.")
add_table(doc, ["Setting", "Implemented value", "Purpose"], [
    ("Criterion", "Gini", "Measures split quality for the two-class decision tree."),
    ("Maximum depth", "8", "Limits complexity and helps readability."),
    ("Minimum samples to split", "20", "Avoids splits based on very small groups."),
    ("Minimum samples per leaf", "10", "Encourages more stable leaf decisions."),
    ("Class weighting", "PASS 1; HOLD 2", "Places additional emphasis on identifying the HOLD class."),
    ("Random state", "42", "Makes the split and training run reproducible."),
    ("Evaluation", "80:20 stratified hold-out plus 5-fold stratified cross-validation", "Preserves the outcome mix during evaluation."),
], widths=[1.55, 1.65, 3.15], font_size=8.9)
add_heading(doc, "6.3 Evaluation results", 2)
add_table(doc, ["Measure", "Held-out test result", "5-fold cross-validation result"], [
    ("Accuracy", "95.42%", "90.08% mean"),
    ("Balanced accuracy", "93.55%", "88.87% mean"),
    ("HOLD precision", "95.52%", "82.35% mean"),
    ("HOLD recall", "88.89%", "85.83% mean"),
    ("HOLD F1 score", "92.09%", "83.96% mean"),
    ("PASS recall", "98.21%", "Not separately reported in cross-validation summary"),
], widths=[1.75, 2.25, 2.35], font_size=9.1)
add_para(doc, "On the held-out 240-record set, the confusion matrix contained 165 PASS predictions correctly identified, 64 HOLD predictions correctly identified, 3 PASS records marked HOLD and 8 HOLD records marked PASS. These figures demonstrate consistency with the rule-derived labels; they do not establish predictive performance on independently collected laboratory data.")
add_heading(doc, "6.4 Application integration", 2)
add_para(doc, "The trained joblib artifact is integrated into the milk workflow as a fallback decision-support model. It checks that fat, SNF, sodium, urea and milk class are available, maps the selected product type to the supported class and returns a PASS or HOLD screen prediction with model confidence. The app provides clear missing-field feedback when the required inputs are incomplete. The intended hierarchy remains: current reference and expert review first; model output as limited supporting information only.")

# Chapter 7
add_heading(doc, "7 Verification results and current status", 1)
add_heading(doc, "7.1 Completed checks", 2)
add_table(doc, ["Area", "Verification completed", "Status"], [
    ("Application code", "Python compilation completed after decision-tree integration.", "Passed"),
    ("Milk assessment logic", "Six automated scenario checks for the assessment function.", "6 of 6 passed"),
    ("AI dataset templates", "Structural dataset validation of milk, fermented and fruit-beverage templates.", "Valid; 0 eligible real labels"),
    ("Decision tree", "Held-out test, 5-fold cross-validation, confusion matrix and readable rules exported.", "Completed"),
    ("CSV usability", "Created Excel-friendly output with UTF-8 BOM and comma separator declaration.", "Completed"),
    ("MySQL", "Local server installed/configured and milk assessment records loaded.", "Completed"),
    ("Live dashboard", "Streamlit application launched locally and confirmed to read recent ThingSpeak sensor data.", "Completed"),
], widths=[1.45, 3.85, 1.05], font_size=8.9)
add_heading(doc, "7.2 Current operational status", 2)
add_para(doc, "The project is operational as a local prototype. The Streamlit dashboard can retrieve ThingSpeak data, and the manual milk-entry and history flows remain available even when ThingSpeak is not configured. The live data flow is particularly valuable for demonstrating how the past IoT module now contributes context to a complete food-quality record rather than existing as a separate sensor exercise.")
add_para(doc, "The current database architecture is intentionally mixed: SQLite is active inside the app, while MySQL proves that the project data can be hosted in a conventional server database. The remaining technical step is to migrate the application data-access layer to MySQL or a managed service if multiple users, remote access, backups and access control are required.")

# Chapter 8
add_heading(doc, "8 Limitations and future development", 1)
add_table(doc, ["Current limitation", "Recommended next step"], [
    ("MQ2/MQ135 values are raw sensor responses.", "Calibrate against appropriate reference instruments; define validated use cases before assigning thresholds or interpreting specific gases."),
    ("The reference rules remain disabled.", "Have a qualified reviewer confirm current legal source, product scope, testing method and amendments before enabling any compliance screen."),
    ("The classifier learned test labels derived from rules.", "Collect independent batches of real, expert-reviewed laboratory results; train and validate on that evidence before any broader use."),
    ("SQLite is used by the running application.", "Migrate the data layer to MySQL or a managed relational service for shared access, backup and role-based control."),
    ("The app is currently a local prototype.", "Deploy securely with secrets management, audit logging, user authentication and an operational backup plan."),
    ("Environmental data are contextual rather than product-specific.", "Run controlled storage and spoilage studies to establish correlations with sample-level quality outcomes."),
], widths=[2.95, 3.4], font_size=9.0)
add_para(doc, "The most valuable next phase is an evidence-building study: collect synchronized sensor, storage and laboratory data from actual milk samples; require expert review; document sampling and test methods; and reserve independent batches for model validation. That would allow FOODIQ to evolve from a well-structured prototype into a scientifically evaluated decision-support system.")

# Chapter 9
add_heading(doc, "9 Conclusion", 1)
add_para(doc, "FOODIQ brings together the work completed across the project: a functioning Arduino-based environmental sensor module, ThingSpeak cloud monitoring, a Streamlit food-quality website, local data storage, carefully scoped FSSAI-reference screening, a clean test dataset and an evaluated decision tree classifier. The result is not simply a dashboard or a standalone hardware prototype; it is an end-to-end traceability workflow that connects live environmental conditions to a milk-quality record and review process.")
add_para(doc, "The project’s strongest design decision is its restraint around quality claims. Sensor signals are presented as raw contextual data, reference values are controlled rather than automatically treated as legal grades, and the classifier is documented as a test-data decision-support model. This creates a sound platform for future calibration, expert-reviewed data collection and production-grade database deployment.")

# References
add_heading(doc, "References and project evidence", 1)
for ref in [
    "FSSAI Food Safety and Standards Food Products Standards and Food Additives Regulations, 2011, Regulation 2.1.2, dairy reference values used in the controlled project configuration. Current official notifications and amendments must be checked before compliance use.",
    "FOODIQ source repository: app.py, quality_rules.json, serial_to_thingspeak.py, training and validation scripts, datasets, model artifact and evaluation reports in the foodiq_starter project folder.",
    "Earlier IoT project report supplied by the author: IoT Spoilage Sensor Module with Integrated Humidity, Temperature, VOC, and Gas Modules, Rohan Biju, URK23FP2013. Used here as the technical record for the reused sensor module."
]: add_bullet(doc, ref)

# Appendices
doc.add_page_break()
add_heading(doc, "Appendix A Project file inventory", 1)
add_table(doc, ["File or folder", "Purpose"], [
    ("app.py", "Main Streamlit application and live dashboard / milk-quality workflow."),
    ("serial_to_thingspeak.py", "Optional USB serial bridge from the Arduino packet to ThingSpeak."),
    ("quality_rules.json", "Controlled milk reference configuration; disabled pending independent review."),
    ("foodiq.db", "Active SQLite observation and expert-review database for the local app."),
    ("ai_datasets/", "Observation templates, validation report and FSSAI-reference test CSV files."),
    ("generate_fssai_synthetic_milk_dataset.py", "Reproducible generation logic for the rule-derived test dataset."),
    ("create_excel_friendly_csv.py", "Creates a CSV variant that opens into separate columns in Excel."),
    ("train_fssai_decision_tree_demo.py", "Decision tree training and evaluation pipeline."),
    ("models/fssai_decision_tree_demo.joblib", "Saved model artifact used by the app."),
    ("reports/", "Evaluation metrics, confusion matrix and readable tree rules."),
    ("prepare_ai_datasets.py and validate_ai_datasets.py", "Expert-label preparation and structural validation for future real-data modelling."),
], widths=[2.45, 3.9], font_size=9.1)
add_heading(doc, "Appendix B FSSAI reference categories used for the test dataset", 1)
add_para(doc, "The following values were used in the project’s reference-driven test-data generator. They are recorded for reproducibility of the project test dataset, not as an instruction to enable a live compliance engine without current independent verification.")
add_table(doc, ["Milk class", "Fat requirement used", "SNF requirement used"], [
    ("Buffalo", "Minimum 5.0%", "Minimum 9.0%"), ("Cow", "Minimum 3.2%", "Minimum 8.3%"),
    ("Goat / Sheep", "Minimum 3.0%", "Minimum 8.0%"), ("Camel", "Minimum 2.0%", "Minimum 6.0%"),
    ("Mixed", "Minimum 4.5%", "Minimum 8.5%"), ("Standardised", "Minimum 4.5%", "Minimum 8.5%"),
    ("Toned", "Minimum 3.0%", "Minimum 8.5%"), ("Double Toned", "Minimum 1.5%", "Minimum 9.0%"),
    ("Skimmed", "Maximum 0.5%", "Minimum 8.7%"), ("Full Cream", "Minimum 6.0%", "Minimum 9.0%"),
], widths=[2.0, 2.15, 2.2], font_size=9.4)
add_para(doc, "The test-data generator also uses total sodium not exceeding 650 mg per 100 g SNF and total urea not exceeding 700 ppm as reference checks. The project keeps these as a dataset and screening context, not as a substitute for the applicable official method, sampling procedure or confirmatory laboratory analysis.")

doc.core_properties.title = "FOODIQ Integrated IoT and Milk Quality Monitoring Project Report"
doc.core_properties.author = "Rohan Biju"
doc.core_properties.subject = "Project report"
doc.save(OUT)
print(OUT)
