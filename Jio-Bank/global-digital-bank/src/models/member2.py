"""
Member2: implements F7-F16 (updated to use CSV transaction helpers)
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from utils.file_manager import TRANSACTIONS_FILE, read_transactions_for_account, log_transaction

class Member2Features:
    def __init__(self, accounts: Dict[int, object], transactions_file: str = TRANSACTIONS_FILE):
        self.accounts = accounts
        self.transactions_file = transactions_file
        # daily_totals keyed by (acc_no, date_str) -> total absolute amount done today
        self._daily_totals = {}
        self.default_daily_limit = 100000.0

    # ---------- F7: Search by Account Number ----------
    def search_by_account_number(self, account_number: int) -> Optional[object]:
        try:
            acc_no = int(account_number)
        except Exception:
            return None
        return self.accounts.get(acc_no)

    # ---------- F8: Minimum Balance Check ----------
    def can_withdraw_without_violating_min(self, acc, amount: float, min_allowed: float = 500.0) -> Tuple[bool, str]:
        try:
            amt = float(amount)
        except Exception:
            return False, "Invalid amount"

        if amt <= 0:
            return False, "Amount must be positive"

        remaining = acc.balance - amt
        if remaining < float(min_allowed):
            return False, f"Would reduce balance below minimum allowed ₹{min_allowed:.2f} (remaining ₹{remaining:.2f})"
        return True, "OK"

    # ---------- F9: Simple Interest ----------
    def simple_interest(self, acc_no: int, rate_percent: float, years: float) -> Tuple[Optional[float], str]:
        acc = self.search_by_account_number(acc_no)
        if not acc:
            return None, "Account not found"
        try:
            r = float(rate_percent) / 100.0
            y = float(years)
        except Exception:
            return None, "Invalid rate/years"
        interest = acc.balance * r * y
        return interest, f"Interest on ₹{acc.balance:.2f} at {rate_percent}% for {years} year(s) is ₹{interest:.2f}"

    # ---------- F10: Daily Transaction Limit ----------
    def check_daily_limit(self, acc_no: int, amount: float, daily_limit: Optional[float] = None) -> Tuple[bool, str]:
        if daily_limit is None:
            daily_limit = self.default_daily_limit
        try:
            acc_no_i = int(acc_no)
            amt = abs(float(amount))
        except Exception:
            return False, "Invalid numeric input"

        date_key = datetime.now().strftime("%Y-%m-%d")
        key = (acc_no_i, date_key)
        current = self._daily_totals.get(key, 0.0)
        if (current + amt) > float(daily_limit):
            return False, f"Daily transaction limit exceeded: {current + amt:.2f} > {daily_limit:.2f}"
        return True, "OK"

    def record_daily_txn(self, acc_no: int, amount: float) -> None:
        try:
            acc_no_i = int(acc_no)
            amt = abs(float(amount))
        except Exception:
            return
        date_key = datetime.now().strftime("%Y-%m-%d")
        key = (acc_no_i, date_key)
        self._daily_totals[key] = self._daily_totals.get(key, 0.0) + amt

    # ---------- F11: Transfer Funds ----------
    def transfer(self, from_acc_no: int, to_acc_no: int, amount: float, min_balance: float = 500.0, log_func=None) -> Tuple[bool, str]:
        # Accept flexible calls (some versions may not pass min_balance/log_func)
        try:
            amt = float(amount)
        except Exception:
            return False, "Invalid amount"

        src = self.search_by_account_number(from_acc_no)
        dst = self.search_by_account_number(to_acc_no)
        if not src:
            return False, "Source account not found"
        if not dst:
            return False, "Destination account not found"
        if not getattr(src, "is_active", lambda: True)() or not getattr(dst, "is_active", lambda: True)():
            return False, "Both accounts must be active"

        # enforce min balance
        remaining = src.balance - amt
        if remaining < float(min_balance):
            return False, f"Would reduce source balance below minimum allowed ₹{min_balance:.2f} (remaining ₹{remaining:.2f})"

        before_src = src.balance
        before_dst = dst.balance
        src.balance -= amt
        dst.balance += amt

        # log if logger provided
        if log_func:
            try:
                log_func(src.account_number, f"TRANSFER_OUT->{dst.account_number}", amt, src.balance)
                log_func(dst.account_number, f"TRANSFER_IN<-{src.account_number}", amt, dst.balance)
            except Exception:
                pass
        else:
            # fallback: use internal transaction log function
            try:
                log_transaction(src.account_number, f"TRANSFER_OUT->{dst.account_number}", amt, src.balance)
                log_transaction(dst.account_number, f"TRANSFER_IN<-{src.account_number}", amt, dst.balance)
            except Exception:
                pass

        return True, f"Transferred ₹{amt:.2f} from {from_acc_no} → {to_acc_no} (src before: ₹{before_src:.2f}, after: ₹{src.balance:.2f})"

    # ---------- F12: Transaction History (uses CSV helper) ----------
    def transaction_history(self, acc_no: int, limit: int = 200) -> Tuple[List[dict], str]:
        try:
            rows = read_transactions_for_account(int(acc_no), limit)
            if not rows:
                return [], "No transactions found for this account"
            return rows, f"{len(rows)} records (most-recent-first)"
        except Exception:
            return [], "Error reading transaction history"

    # ---------- F13: Average Balance ----------
    def average_balance(self) -> float:
        if not self.accounts:
            return 0.0
        total = sum((getattr(a, "balance", 0.0) or 0.0) for a in self.accounts.values())
        return total / max(1, len(self.accounts))

    # ---------- F14: Youngest ----------
    def youngest_account_holder(self):
        if not self.accounts:
            return None
        return min(self.accounts.values(), key=lambda a: getattr(a, "age", 0))

    # ---------- F15: Oldest ----------
    def oldest_account_holder(self):
        if not self.accounts:
            return None
        return max(self.accounts.values(), key=lambda a: getattr(a, "age", 0))

    # ---------- F16: Top N by balance ----------
    def top_n_by_balance(self, n: int = 5) -> List[object]:
        try:
            nn = int(n)
        except Exception:
            nn = 5
        return sorted(self.accounts.values(), key=lambda a: getattr(a, "balance", 0.0), reverse=True)[:nn]