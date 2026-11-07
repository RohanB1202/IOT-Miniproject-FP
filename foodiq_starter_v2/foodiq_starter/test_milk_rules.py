import app

# Temporary test configuration — does not modify quality_rules.json.

def temporary_test_rules():
    return {
        "milk": {
            "enabled": True,
            "hard_limits": [
                {
                    "field": "fat_pct",
                    "allowed": {"min": 3.2},
                    "milk_category": "Raw milk",
                    "milk_product_type": "Cow milk"
                },
                {
                    "field": "snf_pct",
                    "allowed": {"min": 8.3},
                    "milk_category": "Raw milk",
                    "milk_product_type": "Cow milk"
                }
            ],
            "criteria": {}
        }
    }

app.load_rules = temporary_test_rules

def run_test(name, values, expected):
    result = app.classify_by_rules("milk", values)
    status = "PASS" if result[0] == expected else "FAIL"
    print(f"{status}: {name} | Actual: {result[0]}")

# 1. Missing fat
run_test("Missing fat", {
    "milk_category": "Raw milk",
    "milk_product_type": "Cow milk",
    "fat_pct": None,
    "snf_pct": 8.5
}, "Insufficient data")

# 2. Both measurements pass
run_test("Both measurements pass", {
    "milk_category": "Raw milk",
    "milk_product_type": "Cow milk",
    "fat_pct": 3.5,
    "snf_pct": 8.5
}, "Insufficient rules")

# 3. Fat below minimum
run_test("Fat below minimum", {
    "milk_category": "Raw milk",
    "milk_product_type": "Cow milk",
    "fat_pct": 2.8,
    "snf_pct": 8.5
}, "HOLD")

# 4. SNF below minimum
run_test("SNF below minimum", {
    "milk_category": "Raw milk",
    "milk_product_type": "Cow milk",
    "fat_pct": 3.5,
    "snf_pct": 8.0
}, "HOLD")

# 5. Missing SNF
run_test("Missing SNF", {
    "milk_category": "Raw milk",
    "milk_product_type": "Cow milk",
    "fat_pct": 3.5,
    "snf_pct": None
}, "Insufficient data")

# 6. Buffalo milk must not use cow-milk limits
run_test("Buffalo milk exclusion", {
    "milk_category": "Raw milk",
    "milk_product_type": "Buffalo milk",
    "fat_pct": 2.0,
    "snf_pct": 7.0
}, "Insufficient rules")

# 7. Processed milk must not use raw cow-milk limits
run_test("Processed milk exclusion", {
    "milk_category": "Processed milk",
    "milk_product_type": "Toned milk",
    "fat_pct": 2.0,
    "snf_pct": 7.0
}, "Insufficient rules")