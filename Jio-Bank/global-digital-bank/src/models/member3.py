# src/models/member3.py
import csv
from typing import List
from models.account import Account

class Member3Features:
    """
    F13 - Average Balance Calculator
    F14 - Youngest Account Holder
    F15 - Oldest Account Holder
    F16 - Top N Accounts by Balance
    F17 - PIN/Password Protection (basic)
    F18 - Export Accounts to File (CSV)
    """

    def __init__(self, accounts: dict):
        self.accounts = accounts

    # F13
    def average_balance(self):
        if not self.accounts:
            return 0.0
        total = sum(a.balance for a in self.accounts.values())
        count = len(self.accounts)
        avg = total / count
        return avg

    # F14
    def youngest_account_holder(self):
        if not self.accounts:
            return None
        return min(self.accounts.values(), key=lambda a: a.age)

    # F15
    def oldest_account_holder(self):
        if not self.accounts:
            return None
        return max(self.accounts.values(), key=lambda a: a.age)

    # F16
    def top_n_by_balance(self, n=5) -> List[Account]:
        n = int(n)
        return sorted(self.accounts.values(), key=lambda a: a.balance, reverse=True)[:n]

    # F17 - Basic PIN check: expects account.pin to be numeric string or None
    def check_pin(self, acc_no, pin_attempt):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return False, "Account not found"
        if not getattr(acc, "pin", None):
            return False, "No PIN set for this account"
        return (str(acc.pin) == str(pin_attempt)), "PIN check performed"

    def set_pin(self, acc_no, new_pin):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return False, "Account not found"
        acc.pin = str(new_pin)
        return True, "PIN set"

    # F18 - export accounts to CSV
    def export_accounts_csv(self, filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["account_number","name","age","account_type","balance","status","pin"])
            for a in self.accounts.values():
                writer.writerow([a.account_number, a.name, a.age, a.account_type, f"{a.balance:.2f}", a.status, a.pin or ""])
        return True, f"Exported {len(self.accounts)} accounts to {filepath}"