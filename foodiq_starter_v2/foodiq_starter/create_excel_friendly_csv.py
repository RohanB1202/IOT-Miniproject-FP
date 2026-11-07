"""Create an Excel-friendly CSV from the FOODIQ milk-quality dataset.

The ``sep=,`` declaration tells Excel to use commas as delimiters, while the
UTF-8 BOM ensures text opens correctly in Windows Excel.
"""
from __future__ import annotations

import csv
from pathlib import Path


BASE = Path(__file__).parent
SOURCE = BASE / "ai_datasets" / "fssai_milk_quality_dataset.csv"
OUTPUT = BASE / "ai_datasets" / "fssai_milk_quality_dataset_excel.csv"


def main() -> None:
    with SOURCE.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        if not reader.fieldnames:
            raise ValueError("The source CSV does not contain a header row.")

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as output:
        output.write("sep=,\n")
        writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} Excel-ready records to {OUTPUT}")


if __name__ == "__main__":
    main()
