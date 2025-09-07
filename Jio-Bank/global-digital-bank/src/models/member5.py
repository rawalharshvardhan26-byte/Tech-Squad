# src/models/member5.py
import math
from typing import Dict
from datetime import datetime, timedelta

class Member5Features:
    """
    F25 - Loan Eligibility Check (simple rules)
    F26 - Credit Score Mockup (random/simple mapping)
    F27 - EMI Calculator
    F28 - Fixed Deposit Creation & Tracking (simple)
    F29 - Notifications/Alerts (console-level)
    F30 - Admin Dashboard Summary (report view)
    """

    def __init__(self, accounts: Dict[int, object]):
        self.accounts = accounts
        # simple FD store: {fd_id: {...}}
        self._fds = {}
        self._next_fd_id = 1
        self._notifications = []

    # F25 - loan eligibility: simple rule (age, balance, active)
    def loan_eligibility(self, acc_no, requested_amount):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return False, "Account not found"
        if acc.status != "Active":
            return False, "Account not active"
        if acc.age < 21:
            return False, "Must be at least 21 for loan"
        # rule: loan allowed if balance is >= 10% of requested amount
        try:
            amt = float(requested_amount)
        except ValueError:
            return False, "Invalid amount"
        if acc.balance * 10 >= amt:
            return True, f"Eligible up to ₹{acc.balance * 10:.2f}"
        else:
            return False, "Not eligible based on balance"

    # F26 - credit score mock: derive from balance & age
    def credit_score(self, acc_no):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return None, "Account not found"
        # mock: base 300, + (balance/1000) capped and + age factor
        score = 300 + min(400, int(acc.balance / 1000)) + min(300, int(acc.age))
        score = min(900, score)
        return score, f"Mock credit score: {score}"

    # F27 - EMI calculator: EMI = P * r*(1+r)^n / ((1+r)^n - 1)
    def emi(self, principal, annual_rate_percent, years):
        try:
            P = float(principal)
            r = float(annual_rate_percent) / 100.0 / 12.0
            n = int(float(years) * 12)
        except ValueError:
            return None, "Invalid numeric inputs"
        if r == 0:
            emi_val = P / n
        else:
            emi_val = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
        total = emi_val * n
        return emi_val, f"EMI: ₹{emi_val:.2f} over {n} months. Total payable: ₹{total:.2f}"

    # F28 - Fixed Deposit create & list (very lightweight)
    def create_fd(self, acc_no, amount, annual_rate, years):
        acc = self.accounts.get(int(acc_no))
        if not acc:
            return False, "Account not found"
        try:
            amt = float(amount)
            rate = float(annual_rate) / 100.0
            y = float(years)
        except ValueError:
            return False, "Invalid numeric inputs"
        fd_id = self._next_fd_id
        maturity = datetime.now() + timedelta(days=int(y * 365))
        # simple compound annual
        maturity_amount = amt * ((1 + rate) ** y)
        self._fds[fd_id] = {
            "acc_no": acc_no, "amount": amt, "rate": rate, "years": y,
            "maturity": maturity, "maturity_amount": maturity_amount
        }
        self._next_fd_id += 1
        return True, f"FD created: id={fd_id}, maturity amount ₹{maturity_amount:.2f} on {maturity.date()}"

    def list_fds(self, acc_no=None):
        if acc_no:
            acc_id = int(acc_no)
            return {k: v for k, v in self._fds.items() if int(v["acc_no"]) == acc_id}
        return self._fds

    # F29 - simple notifications
    def push_notification(self, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._notifications.append(f"{ts} | {message}")
        print("[NOTIFICATION]", message)

    def get_notifications(self, limit=50):
        return self._notifications[-limit:]

    # F30 - admin dashboard summary
    def admin_summary(self):
        total_accounts = len(self.accounts)
        total_balance = sum(a.balance for a in self.accounts.values())
        active_accounts = sum(1 for a in self.accounts.values() if a.status == "Active")
        closed_accounts = total_accounts - active_accounts
        return {
            "total_accounts": total_accounts,
            "total_balance": total_balance,
            "active_accounts": active_accounts,
            "closed_accounts": closed_accounts,
            "fds": len(self._fds)
        }