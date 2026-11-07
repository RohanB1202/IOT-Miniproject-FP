import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "foodiq.db"

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "observations" not in tables:
            raise RuntimeError("The observations table is missing.")
        if "expert_reviews" not in tables:
            raise RuntimeError("The expert_reviews table is missing.")

        rows = conn.execute("""
            SELECT
                o.id,
                o.batch_id,
                o.module,
                o.product_type,
                o.rule_result,
                o.ai_result,
                r.expert_grade,
                r.reviewed_by,
                r.reviewer_qualification,
                r.label_basis,
                r.review_date
            FROM observations AS o
            LEFT JOIN expert_reviews AS r
                ON r.observation_id = o.id
            ORDER BY o.id
        """).fetchall()

    print("\n========== FOODIQ TRAINING DATA AUDIT ==========")
    print("TOTAL DATABASE OBSERVATIONS:", len(rows))

    counts = {}
    labelled_counts = {}

    for row in rows:
        (record_id, batch_id, module, product_type, rule_result,
         ai_result, expert_grade, reviewed_by, qualification,
         label_basis, review_date) = row

        counts[module] = counts.get(module, 0) + 1
        is_labelled = expert_grade is not None and str(expert_grade).strip() != ""
        if is_labelled:
            labelled_counts[module] = labelled_counts.get(module, 0) + 1

        print("\n--------------------------------")
        print("Record ID:", record_id)
        print("Batch:", batch_id)
        print("Category:", module)
        print("Product:", product_type)
        print("Rule result:", rule_result)
        print("AI result:", ai_result)
        print("Expert grade:", expert_grade if is_labelled else "Not reviewed")

        if is_labelled:
            print("Reviewed by:", reviewed_by)
            print("Reviewer qualification:", qualification)
            print("Assessment basis:", label_basis)
            print("Review date:", review_date)

    print("\n========== CATEGORY SUMMARY ==========")
    for module in ("milk", "fermented", "fruit_beverage"):
        print(
            f"{module} | Observations: {counts.get(module, 0)} "
            f"| Expert-reviewed: {labelled_counts.get(module, 0)}"
        )

    print("\n========== AUDIT COMPLETE ==========")

if __name__ == "__main__":
    main()
