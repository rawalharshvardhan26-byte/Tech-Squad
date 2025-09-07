#!/usr/bin/env python3
"""
Simplified CSV cleaner for Global Digital Bank.

Just run:
    python3 clean_accounts_csv.py

It will:
1. Backup src/data/accounts.csv
2. Clean balances/ages/account_numbers to proper numeric types
3. Overwrite accounts.csv with fixed data
"""

import csv
import shutil
import os
from datetime import datetime

ACCOUNTS_FILE = os.path.join("data", "accounts.csv")


def clean_row(row, line_no):
    cleaned = {}
    row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    # account_number
    cleaned["account_number"] = int(row.get("account_number", 0))

    # name
    cleaned["name"] = row.get("name", "").strip()

    # age
    cleaned["age"] = int(row.get("age", 0))

    # account_type
    cleaned["account_type"] = (row.get("account_type") or "").title()

    # balance
    bal_raw = row.get("balance", "")
    if bal_raw == "" or bal_raw is None:
        cleaned["balance"] = 0.0
    else:
        br = str(bal_raw).replace("₹", "").replace(",", "").strip()
        cleaned["balance"] = float(br)

    # status
    cleaned["status"] = row.get("status", "") or "Active"

    # pin
    cleaned["pin"] = row.get("pin", "") or ""

    return cleaned

def main():
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"ERROR: {ACCOUNTS_FILE} not found")
        return

    backup_path = ACCOUNTS_FILE + ".bak." + datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(ACCOUNTS_FILE, backup_path)
    print(f"Backup created: {backup_path}")

    with open(ACCOUNTS_FILE, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    cleaned_rows = []
    for i, row in enumerate(rows, start=2):
        try:
            cleaned_rows.append(clean_row(row, i))
        except Exception as e:
            print(f"Skipping line {i}: {e}")

    with open(ACCOUNTS_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["account_number","name","age","account_type","balance","status","pin"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in cleaned_rows:
            writer.writerow(r)

    print(f"Cleaned {len(cleaned_rows)} accounts. File overwritten: {ACCOUNTS_FILE}")

if __name__ == "__main__":
    main()
