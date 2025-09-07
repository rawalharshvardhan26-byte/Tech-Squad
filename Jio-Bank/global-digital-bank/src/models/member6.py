# src/models/member6.py
"""
Member6: implements F31-F40 (uses CSV transaction helpers)
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from utils.file_manager import TRANSACTIONS_FILE, log_transaction, read_transactions_for_account

class Member6Features:
    def __init__(self, accounts: Dict[int, object], transactions_file: str = TRANSACTIONS_FILE):
        self.accounts = accounts
        self.transactions_file = Path(transactions_file)
        # scheduled and recurring jobs
        self.scheduled_transfers: List[Dict[str, Any]] = []
        self.recurring_payments: List[Dict[str, Any]] = []
        # beneficiaries per account
        self.beneficiaries: Dict[int, List[Dict[str, Any]]] = {}
        # txn tags
        self.txn_notes: Dict[str, Dict[str, str]] = {}
        # overdraft
        self.overdraft: Dict[int, Dict[str, float]] = {}
        # locks
        self.locked_accounts: set = set()
        # low-balance thresholds
        self.low_balance_thresholds: Dict[int, float] = {}
        # currency map
        self.currency_rates = {
            "INR": 1.0,
            "USD": 0.012,
            "EUR": 0.011,
            "GBP": 0.0095
        }

    # ---------- Beneficiaries ----------
    def add_beneficiary(self, acc_no: int, beneficiary_acc_no: int, nickname: str = "") -> Tuple[bool, str]:
        acc_no = int(acc_no); ben = int(beneficiary_acc_no)
        if ben not in self.accounts:
            return False, "Beneficiary account does not exist"
        self.beneficiaries.setdefault(acc_no, [])
        if any(x["acc"] == ben for x in self.beneficiaries[acc_no]):
            return False, "Beneficiary already added"
        self.beneficiaries[acc_no].append({"acc": ben, "nick": nickname.strip()})
        return True, f"Beneficiary {ben} added"

    def list_beneficiaries(self, acc_no: int) -> List[Dict[str, Any]]:
        return self.beneficiaries.get(int(acc_no), [])

    def remove_beneficiary(self, acc_no: int, beneficiary_acc_no: int) -> Tuple[bool, str]:
        acc_no = int(acc_no); ben = int(beneficiary_acc_no)
        lst = self.beneficiaries.get(acc_no, [])
        new = [x for x in lst if x["acc"] != ben]
        if len(new) == len(lst):
            return False, "Beneficiary not found"
        self.beneficiaries[acc_no] = new
        return True, f"Beneficiary {ben} removed"

    # ---------- Scheduled transfers ----------
    def schedule_transfer(self, from_acc: int, to_acc: int, amount: float, execute_at: datetime) -> Tuple[bool, str]:
        if int(from_acc) not in self.accounts or int(to_acc) not in self.accounts:
            return False, "Account(s) not found"
        self.scheduled_transfers.append({
            "from": int(from_acc), "to": int(to_acc), "amount": float(amount),
            "execute_at": execute_at, "created_at": datetime.now()
        })
        return True, f"Scheduled transfer of ₹{float(amount):.2f} on {execute_at}"

    def list_scheduled_transfers(self) -> List[Dict[str, Any]]:
        return sorted(self.scheduled_transfers, key=lambda x: x["execute_at"])

    def run_due_scheduled_transfers(self, banking_service, now: Optional[datetime] = None) -> Tuple[int, List[str]]:
        now = now or datetime.now()
        executed = []
        remaining = []
        for job in self.scheduled_transfers:
            if job["execute_at"] <= now:
                ok, msg = banking_service.transfer(job["from"], job["to"], job["amount"])
                executed.append(f"{job} -> {ok}:{msg}")
            else:
                remaining.append(job)
        self.scheduled_transfers = remaining
        return len(executed), executed

    # ---------- Recurring ----------
    def add_recurring(self, from_acc: int, to_acc: int, amount: float, interval_days: int, start_date: Optional[datetime]=None) -> Tuple[bool,str]:
        if int(from_acc) not in self.accounts or int(to_acc) not in self.accounts:
            return False, "Account(s) not found"
        job = {
            "from": int(from_acc), "to": int(to_acc), "amount": float(amount),
            "interval_days": int(interval_days),
            "next_run": (start_date or datetime.now()),
            "created_at": datetime.now()
        }
        self.recurring_payments.append(job)
        return True, "Recurring payment added"

    def list_recurring(self):
        return self.recurring_payments

    def cancel_recurring(self, index: int) -> Tuple[bool,str]:
        try:
            self.recurring_payments.pop(index)
            return True, "Cancelled"
        except Exception:
            return False, "Invalid index"

    def run_due_recurring(self, banking_service, now: Optional[datetime]=None) -> Tuple[int, List[str]]:
        now = now or datetime.now()
        logs = []
        for job in list(self.recurring_payments):
            if job["next_run"] <= now:
                ok, msg = banking_service.transfer(job["from"], job["to"], job["amount"])
                logs.append(f"Recurring {job} -> {ok}:{msg}")
                job["next_run"] = job["next_run"] + timedelta(days=job["interval_days"])
        return len(logs), logs

    # ---------- Transaction tags ----------
    def tag_transaction(self, acc_no: int, tx_id: str, tag: str, note: str = "") -> Tuple[bool, str]:
        key = f"{acc_no}|{tx_id}"
        self.txn_notes[key] = {"tag": tag.strip(), "note": note.strip()}
        return True, "Tagged"

    def get_transaction_tag(self, acc_no: int, tx_id: str) -> Optional[Dict[str,str]]:
        return self.txn_notes.get(f"{acc_no}|{tx_id}")

    # ---------- Export statement (CSV) ----------
    def export_statement(self, acc_no: int, start_date: Optional[datetime], end_date: Optional[datetime], out_path: str) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        rows = read_transactions_for_account(acc_no, limit=10000)
        if not rows:
            return False, "No transactions"
        filtered = []
        for r in rows:
            try:
                ts = datetime.strptime(r.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    ts = datetime.fromisoformat(r.get("timestamp", ""))
                except Exception:
                    continue
            if start_date and ts < start_date:
                continue
            if end_date and ts > end_date:
                continue
            filtered.append(r)
        if not filtered:
            return False, "No transactions in range"
        # write to CSV
        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["tx_id","timestamp","account_number","action","amount","balance_after","note"])
                writer.writeheader()
                for rr in reversed(filtered):  # chronological order oldest->newest
                    writer.writerow(rr)
            return True, f"Wrote {len(filtered)} rows to {out_path}"
        except Exception as e:
            return False, f"Failed to write: {e}"

    # ---------- Overdraft ----------
    def set_overdraft(self, acc_no: int, limit: float, fee: float) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        self.overdraft[acc_no] = {"limit": float(limit), "fee": float(fee)}
        return True, f"Overdraft set: limit ₹{limit:.2f}, fee ₹{fee:.2f}"

    def get_overdraft(self, acc_no: int) -> Optional[Dict[str,float]]:
        return self.overdraft.get(int(acc_no))

    # ---------- Lock/Unlock ----------
    def lock_account(self, acc_no: int) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        self.locked_accounts.add(acc_no)
        return True, "Account locked"

    def unlock_account(self, acc_no: int) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        self.locked_accounts.discard(acc_no)
        return True, "Account unlocked"

    # ---------- Reverse last transaction ----------
    def reverse_last_transaction(self, acc_no: int, log_func=None) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        rows = read_transactions_for_account(acc_no, limit=10000)
        if not rows:
            return False, "No transaction file or no transactions for account"
        # last (most recent) is rows[0]
        last = rows[0]
        action = last.get("action", "")
        try:
            amount = float(last.get("amount", 0.0))
        except Exception:
            return False, "Unable to parse amount"
        acc = self.accounts.get(acc_no)
        if not acc:
            return False, "Account not found"
        if "DEPOSIT" in action or "TRANSFER_IN" in action:
            ok, msg = acc.withdraw(amount)
            if ok:
                if log_func:
                    log_func(acc_no, f"REVERSAL->{action}", -amount, acc.balance)
                return True, f"Reversed (subtracted) ₹{amount:.2f}: {msg}"
            return False, msg
        elif "WITHDRAW" in action or "TRANSFER_OUT" in action:
            ok, msg = acc.deposit(amount)
            if ok:
                if log_func:
                    log_func(acc_no, f"REVERSAL->{action}", amount, acc.balance)
                return True, f"Reversed (added) ₹{amount:.2f}: {msg}"
            return False, msg
        else:
            return False, "Action cannot be reversed"

    # ---------- Currency ----------
    def set_account_currency(self, acc_no: int, currency_code: str) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        currency_code = currency_code.upper()
        if currency_code not in self.currency_rates:
            return False, "Unsupported currency"
        acc = self.accounts.get(acc_no)
        if not acc:
            return False, "Account not found"
        setattr(acc, "currency", currency_code)
        return True, f"Account currency set to {currency_code}"

    def convert_balance(self, acc_no: int, to_currency: str) -> Tuple[Optional[float], str]:
        acc_no = int(acc_no)
        to_currency = to_currency.upper()
        if to_currency not in self.currency_rates:
            return None, "Unsupported currency"
        acc = self.accounts.get(acc_no)
        if not acc:
            return None, "Account not found"
        from_currency = getattr(acc, "currency", "INR")
        in_inr = acc.balance * (1.0 / self.currency_rates.get(from_currency, 1.0))
        converted = in_inr * self.currency_rates[to_currency]
        return converted, f"{converted:.2f} {to_currency}"

    # ---------- Low-balance alerts ----------
    def set_low_balance_threshold(self, acc_no: int, threshold: float) -> Tuple[bool,str]:
        acc_no = int(acc_no)
        self.low_balance_thresholds[acc_no] = float(threshold)
        return True, f"Threshold set ₹{threshold:.2f}"

    def check_and_get_low_balance_alerts(self) -> List[str]:
        alerts = []
        for acc_no, thr in self.low_balance_thresholds.items():
            acc = self.accounts.get(acc_no)
            if not acc:
                continue
            if acc.balance < thr:
                alerts.append(f"Account {acc_no} balance ₹{acc.balance:.2f} below threshold ₹{thr:.2f}")
        return alerts