import ast
import pandas as pd
from pathlib import Path

# Load the real assessment function from app.py without launching Streamlit.
source = Path("app.py").read_text(encoding="utf-8")
tree = ast.parse(source)

function = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "classify_by_rules"
)

namespace = {
    "pd": pd,
    "load_rules": lambda: {"milk": {"enabled": False}}
}

exec(
    compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"),
    namespace
)

assess = namespace["classify_by_rules"]

tests = [
    (
        "Cow milk: both reference minima met",
        {"milk_category": "Raw milk", "milk_product_type": "Cow milk",
         "fat_pct": 3.5, "snf_pct": 8.5},
        "REFERENCE CHECK"
    ),
    (
        "Cow milk: fat below minimum",
        {"milk_category": "Raw milk", "milk_product_type": "Cow milk",
         "fat_pct": 3.0, "snf_pct": 8.5},
        "REFERENCE DEVIATION"
    ),
    (
        "Buffalo milk: fat below minimum",
        {"milk_category": "Raw milk", "milk_product_type": "Buffalo milk",
         "fat_pct": 4.5, "snf_pct": 9.5},
        "REFERENCE DEVIATION"
    ),
    (
        "Cow milk: SNF missing",
        {"milk_category": "Raw milk", "milk_product_type": "Cow milk",
         "fat_pct": 3.5, "snf_pct": None},
        "INSUFFICIENT DATA"
    ),
    (
        "Failed adulteration screen",
        {"milk_category": "Raw milk", "milk_product_type": "Cow milk",
         "fat_pct": 3.5, "snf_pct": 8.5,
         "starch_screen": "Fail / suspected positive"},
        "HOLD"
    ),
    (
        "Inconclusive adulteration screen",
        {"milk_category": "Raw milk", "milk_product_type": "Cow milk",
         "fat_pct": 3.5, "snf_pct": 8.5,
         "urea_screen": "Inconclusive"},
        "REVIEW"
    )
]

print("\n========== FOODIQ MILK VALIDATION ==========\n")

passed = 0

for name, values, expected in tests:
    result, explanation = assess("milk", values)
    success = expected in result.upper()

    print(("PASS" if success else "FAIL") + " | " + name)
    print("       Actual:   " + result)
    print("       Expected: " + expected)

    if success:
        passed += 1

    print()

print("========== SUMMARY ==========")
print(f"Passed: {passed}/{len(tests)}")
print(f"Failed: {len(tests) - passed}/{len(tests)}")

if passed != len(tests):
    raise SystemExit("VALIDATION FAILED: Review the failed scenarios.")

print("\nALL SIX MILK ASSESSMENT TESTS PASSED.")
