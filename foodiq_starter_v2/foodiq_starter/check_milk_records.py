import sqlite3
import json

DB_PATH = "foodiq.db"

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row

    records = conn.execute("""
        SELECT id, batch_id, module, product_type,
               created_at, rule_result, ai_result, payload
        FROM observations
        WHERE module = 'milk'
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

print("\n========== MILK DATABASE CHECK ==========")
print("Total recent milk records:", len(records))

for record in records:
    print("\n----------------------------------------")
    print("Record ID:", record["id"])
    print("Batch ID:", record["batch_id"])
    print("Product:", record["product_type"])
    print("Date:", record["created_at"])
    print("Rule result:", record["rule_result"])
    print("AI result:", record["ai_result"])

    payload = json.loads(record["payload"])

    print("Fat:", payload.get("fat_pct"))
    print("SNF:", payload.get("snf_pct"))
    print("pH:", payload.get("ph"))
    print("Milk category:", payload.get("milk_category"))
    print("Milk type:", payload.get("milk_product_type"))
    print("IoT snapshot:", payload.get("iot_snapshot"))

print("\n========== CHECK COMPLETE ==========")