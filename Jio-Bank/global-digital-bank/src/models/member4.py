# src/models/member4.py
import csv
from typing import Dict
from models.account import Account

class Member4Features:
    """
    F19 - Age Verification at Creation (helper)
    F20 - Rename Account Holder
    F21 - Count Active Accounts
    F22 - Delete All Accounts (admin)
    F23 - System Exit with Autosave (helper)
    F24 - Import Accounts from File (CSV)
    """

    def __init__(self, accounts: Dict[int, Account]):
        self.accounts = accounts

    # F19 - verify age >= 18
    def verify_age(self, age) -> (bool, str):
        try:
            a = int(age)
        except ValueError:
            return False, "Invalid age"
        if a < 18:
            return False, "Age must be at least 18"
        return True, "OK"

    # F20 - rename
    def rename_account(self, acc_no, new_name):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return False, "Account not found"
        acc.name = new_name.strip()
        return True, f"Account {acc_no} name changed to {acc.name}"

    # F21 - count active
    def count_active_accounts(self):
        return sum(1 for a in self.accounts.values() if a.status == "Active")

    # F22 - delete all (admin-only): caller should ensure admin auth
    def delete_all_accounts(self):
        count = len(self.accounts)
        self.accounts.clear()
        return True, f"Deleted {count} accounts"

    # F23 - autosave is handled in service; helper included to show intention
    def prepare_exit_summary(self):
        # e.g., return counts and totals for final report
        total_accounts = len(self.accounts)
        total_balance = sum(a.balance for a in self.accounts.values())
        return {
            "total_accounts": total_accounts,
            "total_balance": total_balance,
            "active_accounts": sum(1 for a in self.accounts.values() if a.status == "Active")
        }

    # F24 - import accounts from CSV (expects same format as export)
    def import_from_csv(self, filepath):
        imported = 0
        try:
            with open(filepath, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        acc_no = int(row["account_number"])
                        acc = Account(
                            acc_no,
                            row["name"],
                            int(row["age"]),
                            row["account_type"],
                            float(row.get("balance", 0.0)),
                            status=row.get("status", "Active"),
                            pin=row.get("pin") if row.get("pin") else None
                        )
                        self.accounts[acc_no] = acc
                        imported += 1
                    except Exception:
                        continue
            return True, f"Imported {imported} accounts from {filepath}"
        except FileNotFoundError:
            return False, "File not found"