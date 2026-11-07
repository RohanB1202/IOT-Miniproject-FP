import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart

BASE = Path(r"C:\Users\ASUS\OneDrive\Documents\foodiq_starter_v2\foodiq_starter")
OUT = Path(r"C:\Users\ASUS\OneDrive\Documents\foodiq_starter_v2\FOODIQ_Decision_Tree_Model_Evaluation_Report.pdf")
WORK = Path(r"C:\Users\ASUS\OneDrive\Documents\foodiq_starter_v2\report_work\model_metrics")
WORK.mkdir(parents=True, exist_ok=True)
METRICS = json.loads((BASE / "reports" / "fssai_decision_tree_demo_metrics.json").read_text(encoding="utf-8"))

NAVY = "#17365D"
MID_BLUE = "#2F75B5"
LIGHT_BLUE = "#DCE6F1"
PALE = "#F4F7FA"
ORANGE = "#E67E22"
GREEN = "#2E8B57"
RED = "#C0392B"


def pct(v):
    return f"{v * 100:.2f}%"


def make_metric_chart():
    h = METRICS["held_out_test"]
    cv = METRICS["cross_validation_5_fold"]
    labels = ["Accuracy", "Balanced\naccuracy", "HOLD\nprecision", "HOLD\nrecall", "HOLD F1"]
    held = [h["accuracy"], h["balanced_accuracy"], h["hold_precision"], h["hold_recall"], h["hold_f1"]]
    means = [cv["accuracy"]["mean"], cv["balanced_accuracy"]["mean"], cv["hold_precision"]["mean"], cv["hold_recall"]["mean"], cv["hold_f1"]["mean"]]
    stds = [cv["accuracy"]["std"], cv["balanced_accuracy"]["std"], cv["hold_precision"]["std"], cv["hold_recall"]["std"], cv["hold_f1"]["std"]]
    d = Drawing(500, 245)
    chart = VerticalBarChart(); chart.x = 55; chart.y = 45; chart.width = 410; chart.height = 160
    chart.data = [[x*100 for x in held], [x*100 for x in means]]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "Helvetica"; chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0; chart.valueAxis.valueMax = 105; chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontSize = 7; chart.valueAxis.labels.fontName = "Helvetica"
    chart.bars[0].fillColor = colors.HexColor(MID_BLUE); chart.bars[1].fillColor = colors.HexColor(ORANGE)
    chart.groupSpacing = 9; chart.barSpacing = 2
    d.add(chart)
    d.add(String(55, 222, "Held-out test", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor(MID_BLUE)))
    d.add(String(145, 222, "5-fold CV mean", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor(ORANGE)))
    d.add(String(245, 222, "Scores in percent", fontName="Helvetica-Oblique", fontSize=8, fillColor=colors.HexColor("#555555")))
    return d


def make_confusion_chart():
    import csv
    with (BASE / "reports" / "fssai_decision_tree_demo_confusion_matrix.csv").open(newline="") as f:
        rows = list(csv.reader(f))[1:]
    matrix = [[int(rows[0][1]), int(rows[0][2])], [int(rows[1][1]), int(rows[1][2])]]
    d = Drawing(355, 265); d.add(String(104, 244, "Held-out Test Confusion Matrix", fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor(NAVY)))
    d.add(String(145, 220, "Predicted PASS", fontName="Helvetica-Bold", fontSize=9)); d.add(String(241, 220, "Predicted HOLD", fontName="Helvetica-Bold", fontSize=9))
    d.add(String(12, 170, "Actual PASS", fontName="Helvetica-Bold", fontSize=9)); d.add(String(10, 112, "Actual HOLD", fontName="Helvetica-Bold", fontSize=9))
    values = [matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]]; maxv=max(values)
    coords = [(125,145),(220,145),(125,85),(220,85)]
    for (x,y), val in zip(coords, values):
        shade = 0.18 + 0.72*(val/maxv)
        fill = colors.Color(0.15*(1-shade)+0.05, 0.45*(1-shade)+0.25, 0.78*(1-shade)+0.5)
        d.add(Rect(x,y,82,52,fillColor=fill,strokeColor=colors.white))
        d.add(String(x+35,y+20,str(val),fontName="Helvetica-Bold",fontSize=18,fillColor=colors.white if val>maxv*.45 else colors.HexColor(NAVY)))
    d.add(String(114, 43, "Rows = actual labels; columns = predicted labels", fontName="Helvetica-Oblique", fontSize=8, fillColor=colors.HexColor("#555555")))
    return d, matrix


metric_chart = make_metric_chart()
confusion_chart, matrix = make_confusion_chart()

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="RptTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27,
                          textColor=colors.HexColor(NAVY), alignment=TA_CENTER, spaceAfter=8))
styles.add(ParagraphStyle(name="RptSub", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=15,
                          alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceAfter=12))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=19,
                          textColor=colors.HexColor(NAVY), spaceBefore=8, spaceAfter=7))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14,
                          textColor=colors.HexColor(NAVY), spaceBefore=6, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=14,
                          spaceAfter=7, textColor=colors.HexColor("#222222")))
styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8.4, leading=11,
                          textColor=colors.HexColor("#444444"), spaceBefore=5, spaceAfter=6))


def table(data, widths, header=True, font=8.4):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER")
    cmds = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), font),
            ("LEADING", (0, 0), (-1, -1), font + 2.4), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                 ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (1, 1), (-1, -1), "CENTER")]
        for r in range(1, len(data)):
            if r % 2 == 0: cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(PALE)))
    t.setStyle(TableStyle(cmds)); return t


def footer(canvas, doc):
    canvas.saveState(); canvas.setStrokeColor(colors.HexColor(NAVY)); canvas.setLineWidth(.5)
    canvas.line(doc.leftMargin, 0.47*inch, A4[0] - doc.rightMargin, 0.47*inch)
    canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(doc.leftMargin, 0.3*inch, "FOODIQ - Decision Tree Model Evaluation")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.3*inch, f"Page {doc.page}")
    canvas.restoreState()


story = []
story += [Spacer(1, .7*inch), Paragraph("FOODIQ", styles["RptTitle"]),
          Paragraph("Decision Tree Model Evaluation Report", styles["RptTitle"]),
          Paragraph("Milk composition screening model based on the project test dataset", styles["RptSub"]), Spacer(1, .22*inch)]

overview = [
    ["Model", "DecisionTreeClassifier"],
    ["Dataset", "1,200 rule-derived milk-composition test records"],
    ["Features", "Fat, SNF, total sodium, total urea and milk class"],
    ["Target", "PASS or HOLD composition-screen result"],
    ["Evaluation", "80:20 stratified held-out test and 5-fold stratified cross-validation"],
]
story.append(table([["Evaluation scope", "Value"]] + overview, [1.75*inch, 4.55*inch], font=9))
story.append(Spacer(1, .26*inch))
story.append(Paragraph("Executive summary", styles["H1x"]))
story.append(Paragraph(
    f"The model achieved <b>{pct(METRICS['held_out_test']['accuracy'])}</b> accuracy on the held-out test set and "
    f"<b>{pct(METRICS['cross_validation_5_fold']['accuracy']['mean'])}</b> mean accuracy in 5-fold cross-validation. "
    f"It correctly identified {matrix[1][1]} of {sum(matrix[1])} HOLD records in the held-out set, giving a HOLD recall of "
    f"<b>{pct(METRICS['held_out_test']['hold_recall'])}</b>.", styles["Bodyx"]))
story.append(Paragraph(
    "Interpretation: these results measure agreement with rule-derived test labels. The model is an in-app decision-support demonstration and does not replace FSSAI verification, accredited laboratory testing, or expert review.", styles["Note"]))
story.append(Spacer(1, .08*inch))
story.append(Paragraph("Key held-out test results", styles["H2x"]))
held = METRICS["held_out_test"]
keyrows = [["Metric", "Result", "What it indicates"],
    ["Accuracy", pct(held["accuracy"]), "Overall correct predictions across PASS and HOLD."],
    ["Balanced accuracy", pct(held["balanced_accuracy"]), "Average class-aware performance despite class imbalance."],
    ["HOLD precision", pct(held["hold_precision"]), "How often a predicted HOLD was actually HOLD."],
    ["HOLD recall", pct(held["hold_recall"]), "How many actual HOLD records were detected."],
    ["HOLD F1 score", pct(held["hold_f1"]), "Balance between HOLD precision and recall."],
    ["PASS recall", pct(held["pass_recall"]), "How many actual PASS records were detected."],
]
story.append(table(keyrows, [1.45*inch, 1.05*inch, 3.8*inch], font=8.5))
story.append(PageBreak())

story.append(Paragraph("Performance comparison", styles["H1x"]))
story.append(Paragraph("The chart compares the held-out test scores with the mean of five stratified cross-validation folds. Error bars on the orange bars show the cross-validation standard deviation.", styles["Bodyx"]))
story.append(metric_chart)
story.append(Spacer(1, .08*inch))
cv = METRICS["cross_validation_5_fold"]
cvrows = [["Metric", "5-fold mean", "Standard deviation"],
    ["Accuracy", pct(cv["accuracy"]["mean"]), pct(cv["accuracy"]["std"])],
    ["Balanced accuracy", pct(cv["balanced_accuracy"]["mean"]), pct(cv["balanced_accuracy"]["std"])],
    ["HOLD precision", pct(cv["hold_precision"]["mean"]), pct(cv["hold_precision"]["std"])],
    ["HOLD recall", pct(cv["hold_recall"]["mean"]), pct(cv["hold_recall"]["std"])],
    ["HOLD F1 score", pct(cv["hold_f1"]["mean"]), pct(cv["hold_f1"]["std"])],
]
story.append(Paragraph("Cross-validation summary", styles["H2x"]))
story.append(table(cvrows, [2.3*inch, 1.9*inch, 1.9*inch], font=8.7))
story.append(Spacer(1, .15*inch))
story.append(Paragraph("Confusion matrix", styles["H1x"]))
story.append(Paragraph("Rows show actual labels and columns show predicted labels. Correct predictions lie on the diagonal.", styles["Bodyx"]))
story.append(confusion_chart)
story.append(PageBreak())

story.append(Paragraph("Model configuration and evaluation notes", styles["H1x"]))
p = METRICS["tree_parameters"]
config = [["Parameter", "Configured value"],
    ["Criterion", str(p["criterion"])], ["Maximum depth", str(p["max_depth"])],
    ["Minimum samples to split", str(p["min_samples_split"])], ["Minimum samples per leaf", str(p["min_samples_leaf"])],
    ["Class weighting", "PASS: 1, HOLD: 2"], ["Random state", str(p["random_state"])],
    ["Training / test split", "960 / 240 records, stratified"],
]
story.append(table(config, [2.6*inch, 3.5*inch], font=9))
story.append(Spacer(1, .18*inch))
story.append(Paragraph("Held-out confusion matrix values", styles["H2x"]))
cmrows = [["Actual label", "Predicted PASS", "Predicted HOLD", "Total"],
    ["PASS", str(matrix[0][0]), str(matrix[0][1]), str(sum(matrix[0]))],
    ["HOLD", str(matrix[1][0]), str(matrix[1][1]), str(sum(matrix[1]))],
    ["Total", str(matrix[0][0] + matrix[1][0]), str(matrix[0][1] + matrix[1][1]), str(sum(sum(r) for r in matrix))],
]
story.append(table(cmrows, [1.55*inch, 1.55*inch, 1.55*inch, 1.1*inch], font=9))
story.append(Spacer(1, .22*inch))
story.append(Paragraph("Reading the results", styles["H2x"]))
for txt in [
    "The stronger PASS recall means that 165 of 168 PASS cases in the held-out split were recognised as PASS.",
    "Eight actual HOLD cases were predicted as PASS. In a quality-screening setting, this type of error is important and should be reviewed rather than treated as an automated approval.",
    "The model features intentionally exclude the rule-limit columns and failure-reason text, avoiding direct leakage of the generated label into the prediction.",
    "The exported project artifacts include the full metric JSON, a CSV confusion matrix, a readable tree-rules text file and the saved joblib model.",
]: story.append(Paragraph("- " + txt, styles["Bodyx"]))
story.append(Spacer(1, .12*inch))
story.append(Paragraph("Source files used", styles["H2x"]))
story.append(Paragraph(
    "reports/fssai_decision_tree_demo_metrics.json; reports/fssai_decision_tree_demo_confusion_matrix.csv; "
    "train_fssai_decision_tree_demo.py; models/fssai_decision_tree_demo.joblib.", styles["Note"]))

pdf = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=.72*inch, leftMargin=.72*inch, topMargin=.65*inch, bottomMargin=.62*inch)
pdf.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
