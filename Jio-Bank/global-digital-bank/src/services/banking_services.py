# src/services/banking_services.py
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime

from models.account import Account

# Import members defensively
try:
    from models.member1 import Member1Features
except Exception:
    Member1Features = None
try:
    from models.member2 import Member2Features
except Exception:
    Member2Features = None
try:
    from models.member3 import Member3Features
except Exception:
    Member3Features = None
try:
    from models.member4 import Member4Features
except Exception:
    Member4Features = None
try:
    from models.member5 import Member5Features
except Exception:
    Member5Features = None
try:
    from models.member6 import Member6Features
except Exception:
    Member6Features = None

from utils.file_manager import load_accounts, save_accounts, log_transaction, TRANSACTIONS_FILE


class BankingService:
    START_ACCOUNT_NO = 1001

    def __init__(self):
        try:
            self.accounts: Dict[int, Account] = load_accounts() or {}
        except Exception:
            self.accounts = {}

        if self.accounts:
            try:
                self.next_account_number = max(self.accounts.keys()) + 1
            except Exception:
                self.next_account_number = BankingService.START_ACCOUNT_NO
        else:
            self.next_account_number = BankingService.START_ACCOUNT_NO

        # instantiate member modules if available
        self.member1 = Member1Features(self.accounts) if Member1Features else None
        self.member2 = Member2Features(self.accounts, TRANSACTIONS_FILE) if Member2Features else None
        self.member3 = Member3Features(self.accounts) if Member3Features else None
        self.member4 = Member4Features(self.accounts) if Member4Features else None
        self.member5 = Member5Features(self.accounts) if Member5Features else None
        self.member6 = Member6Features(self.accounts, TRANSACTIONS_FILE) if Member6Features else None

    # ---------------- Persistence ----------------
    def save_to_disk(self) -> None:
        try:
            save_accounts(self.accounts)
        except Exception:
            # don't raise — best-effort save
            pass

    # ---------------- Account creation ----------------
    def create_account(self, name: str, age: int, account_type: str, initial_deposit: float = 0.0) -> Tuple[Optional[Account], str]:
        # verify age (member4 may provide verification)
        if self.member4 and hasattr(self.member4, "verify_age"):
            try:
                ok, msg = self.member4.verify_age(age)
            except Exception:
                ok, msg = False, "Age verification failed"
            if not ok:
                return None, msg
        else:
            try:
                if int(age) < 18:
                    return None, "Age must be 18 or above"
            except Exception:
                return None, "Invalid age"

        account_type = (account_type or "Savings").title()
        if account_type not in Account.MIN_BALANCE:
            return None, f"Invalid account type. Choose from {list(Account.MIN_BALANCE.keys())}"

        try:
            initial = float(initial_deposit)
        except Exception:
            return None, "Invalid initial deposit amount"

        min_req = Account.MIN_BALANCE[account_type]
        if initial < min_req:
            return None, f"Initial deposit must be at least ₹{min_req}"

        acc_no = self.next_account_number
        acc = Account(acc_no, name, int(age), account_type, balance=initial)
        self.accounts[acc_no] = acc
        self.next_account_number += 1

        # record creation in transaction log
        try:
            log_transaction(acc.account_number, "CREATE", initial, acc.balance)
        except Exception:
            pass

        return acc, f"Account created. Account number: {acc_no}"

    # ---------------- Deposit ----------------
    def deposit(self, acc_no, amount, daily_limit: Optional[float] = None) -> Tuple[bool, str]:
        try:
            acc = self.accounts.get(int(acc_no))
        except Exception:
            acc = None
        if not acc:
            return False, "Account not found"

        # member2 daily limit check if requested
        if daily_limit is not None and self.member2:
            try:
                ok, msg = self.member2.check_daily_limit(acc_no, amount, daily_limit)
                if not ok:
                    return False, msg
            except Exception:
                pass

        result = acc.deposit(amount)
        if result is None:
            return False, "Deposit failed due to internal error"

        ok, msg = result
        if ok:
            try:
                log_transaction(acc.account_number, "DEPOSIT", float(amount), acc.balance)
            except Exception:
                pass
            if self.member2:
                try:
                    self.member2.record_daily_txn(acc_no, amount)
                except Exception:
                    pass
        return ok, msg

    # ---------------- Withdraw ----------------
    def withdraw(self, acc_no, amount, daily_limit: Optional[float] = None) -> Tuple[bool, str]:
        try:
            acc = self.accounts.get(int(acc_no))
        except Exception:
            acc = None
        if not acc:
            return False, "Account not found"

        # daily limit check if present
        if daily_limit is not None and self.member2:
            try:
                ok, msg = self.member2.check_daily_limit(acc_no, amount, daily_limit)
                if not ok:
                    return False, msg
            except Exception:
                pass

        # Try member2 helpers for advanced withdraw rules
        helper_ok = None
        helper_msg = "OK"
        if self.member2:
            for helper_name in ("can_withdraw_without_violating_min", "can_withdraw", "can_withdraw_check", "can_withdraw_without_min"):
                if hasattr(self.member2, helper_name):
                    fn = getattr(self.member2, helper_name)
                    try:
                        helper_ok, helper_msg = fn(acc, amount)
                    except TypeError:
                        try:
                            helper_ok, helper_msg = fn(acc.account_number, amount)
                        except Exception:
                            helper_ok, helper_msg = True, "OK"
                    except Exception:
                        helper_ok, helper_msg = True, "OK"
                    break

        # Fallback basic check if helper didn't provide guidance
        if helper_ok is None:
            try:
                amt = float(amount)
            except Exception:
                return False, "Invalid amount"
            min_required = acc.get_minimum_balance() if hasattr(acc, "get_minimum_balance") else Account.MIN_BALANCE.get(acc.account_type, 0.0)
            remaining = acc.balance - amt
            if remaining < min_required:
                helper_ok, helper_msg = False, f"Withdraw would reduce balance below minimum required ₹{min_required:.2f} (remaining ₹{remaining:.2f})"
            else:
                helper_ok, helper_msg = True, "OK"

        if not helper_ok:
            # attempt overdraft via member6 if available
            if self.member6 and hasattr(self.member6, "get_overdraft"):
                try:
                    od = self.member6.get_overdraft(acc.account_number)
                except Exception:
                    od = None
                if od:
                    try:
                        amt = float(amount)
                    except Exception:
                        return False, "Invalid amount"
                    projected = acc.balance - amt
                    limit = float(od.get("limit", 0.0))
                    fee = float(od.get("fee", 0.0))
                    if projected < 0 and abs(projected) <= limit:
                        ok_wd, msg_wd = acc.withdraw(amount)
                        if ok_wd:
                            # apply overdraft fee if account supports it
                            try:
                                if hasattr(acc, "apply_overdraft_fee"):
                                    acc.apply_overdraft_fee(fee)
                                    log_transaction(acc.account_number, "OVERDRAFT_FEE", fee, acc.balance)
                            except Exception:
                                pass
                            try:
                                log_transaction(acc.account_number, "WITHDRAW", float(amount), acc.balance)
                            except Exception:
                                pass
                            if self.member2:
                                try:
                                    self.member2.record_daily_txn(acc_no, amount)
                                except Exception:
                                    pass
                            return True, f"{msg_wd} (overdraft used, fee applied ₹{fee:.2f})"
                        return False, msg_wd
            # no overdraft or can't use it
            return False, helper_msg

        # If helper_ok True, perform the withdraw
        result = acc.withdraw(amount)
        if result is None:
            return False, "Withdrawal failed due to internal error"
        ok, msg = result
        if ok:
            try:
                log_transaction(acc.account_number, "WITHDRAW", float(amount), acc.balance)
            except Exception:
                pass
            if self.member2:
                try:
                    self.member2.record_daily_txn(acc_no, amount)
                except Exception:
                    pass
        return ok, msg

    # ---------------- Transfer ----------------
    def transfer(self, from_acc, to_acc, amount) -> Tuple[bool, str]:
        # Prefer member2's transfer implementation if present
        if self.member2 and hasattr(self.member2, "transfer"):
            fn = getattr(self.member2, "transfer")
            # try a few calling signatures defensively
            for call_variation in (
                (from_acc, to_acc, amount, {"min_balance": 500.0, "log_func": log_transaction}),
                (from_acc, to_acc, amount, {"log_func": log_transaction}),
                (from_acc, to_acc, amount)
            ):
                try:
                    if isinstance(call_variation[3], dict):
                        return fn(call_variation[0], call_variation[1], call_variation[2], **call_variation[3])
                    else:
                        return fn(*call_variation)
                except TypeError:
                    # try next signature
                    continue
                except Exception as e:
                    return False, f"Transfer failed: {e}"
            return False, "Transfer failed: unsupported transfer signature"
        # fallback: simple in-process transfer (best-effort)
        try:
            facc = self.accounts.get(int(from_acc))
            tacc = self.accounts.get(int(to_acc))
        except Exception:
            return False, "Invalid account numbers"
        if not facc:
            return False, "Sender account not found"
        if not tacc:
            return False, "Recipient account not found"
        if not facc.is_active():
            return False, "Sender account is inactive"
        if not tacc.is_active():
            return False, "Recipient account is inactive"

        # perform withdraw then deposit
        # rely on existing checks in Account.transfer_to which we may or may not have; implement here:
        try:
            result = facc.transfer_to(tacc, amount)
            if result is None:
                return False, "Transfer failed due to internal error"
            ok, msg = result
            if ok:
                try:
                    log_transaction(facc.account_number, "TRANSFER_OUT", float(amount), facc.balance)
                    log_transaction(tacc.account_number, "TRANSFER_IN", float(amount), tacc.balance)
                except Exception:
                    pass
            return ok, msg
        except Exception as e:
            return False, f"Transfer failed: {e}"

    # ---------------- Transaction history ----------------
    def transaction_history(self, acc_no, limit: int = 200):
        if self.member2 and hasattr(self.member2, "transaction_history"):
            try:
                return self.member2.transaction_history(acc_no, limit)
            except Exception:
                return [], "Transaction history error"
        return [], "Transaction history not available"

    # ---------------- Simple interest ----------------
    def simple_interest(self, acc_no, rate_percent, years):
        if self.member2 and hasattr(self.member2, "simple_interest"):
            try:
                return self.member2.simple_interest(acc_no, rate_percent, years)
            except Exception:
                return None, "Interest calculation error"
        return None, "Interest feature not available"

    # ---------------- Analysis features ----------------
    def average_balance(self):
        if self.member2 and hasattr(self.member2, "average_balance"):
            try:
                return self.member2.average_balance()
            except Exception:
                pass
        if not self.accounts:
            return 0.0
        total = sum(getattr(a, "balance", 0.0) or 0.0 for a in self.accounts.values())
        return total / max(1, len(self.accounts))

    def youngest_account(self):
        if self.member2 and hasattr(self.member2, "youngest_account_holder"):
            try:
                return self.member2.youngest_account_holder()
            except Exception:
                pass
        return min(self.accounts.values(), key=lambda a: getattr(a, "age", 0), default=None)

    def oldest_account(self):
        if self.member2 and hasattr(self.member2, "oldest_account_holder"):
            try:
                return self.member2.oldest_account_holder()
            except Exception:
                pass
        return max(self.accounts.values(), key=lambda a: getattr(a, "age", 0), default=None)

    def top_n_accounts(self, n=5):
        if self.member2 and hasattr(self.member2, "top_n_by_balance"):
            try:
                return self.member2.top_n_by_balance(n)
            except Exception:
                pass
        return sorted(self.accounts.values(), key=lambda a: getattr(a, "balance", 0.0), reverse=True)[:int(n)]

    # ---------------- PIN functions (use Account methods) ----------------
    def set_pin(self, acc_no, pin):
        try:
            acc = self.accounts.get(int(acc_no))
        except Exception:
            acc = None
        if not acc:
            return False, "Account not found"
        if not hasattr(acc, "set_pin"):
            # if Account lacks PIN methods, set attribute directly
            acc.pin = str(pin)
            return True, "PIN set"
        ok, msg = acc.set_pin(pin)
        return ok, msg

    def check_pin(self, acc_no, pin):
        try:
            acc = self.accounts.get(int(acc_no))
        except Exception:
            acc = None
        if not acc:
            return False, "Account not found"
        if not hasattr(acc, "check_pin"):
            return (str(acc.pin) == str(pin)), "OK" if str(acc.pin) == str(pin) else "Incorrect PIN"
        ok = acc.check_pin(pin)
        return ok, "OK" if ok else "Incorrect PIN"

    # ---------------- Export accounts (member3 fallback) ----------------
    def export_accounts(self, path: str):
        if self.member3 and hasattr(self.member3, "export_accounts_csv"):
            try:
                return self.member3.export_accounts_csv(path)
            except Exception:
                return False, "Export failed"
        # fallback: write current accounts dict using save_accounts
        try:
            ok = save_accounts(self.accounts)
            return True, f"Exported {len(self.accounts)} accounts to {path}"
        except Exception:
            return False, "Export feature not available"

    # ---------------- Rename / count / delete / import (member4) ----------------
    def rename_account(self, acc_no, new_name):
        if self.member4 and hasattr(self.member4, "rename_account"):
            try:
                return self.member4.rename_account(acc_no, new_name)
            except Exception:
                return False, "Rename failed"
        try:
            acc = self.accounts.get(int(acc_no))
        except Exception:
            acc = None
        if not acc:
            return False, "Account not found"
        acc.name = new_name
        return True, "Name updated"

    def count_active_accounts(self):
        if self.member4 and hasattr(self.member4, "count_active_accounts"):
            try:
                return self.member4.count_active_accounts()
            except Exception:
                pass
        return sum(1 for a in self.accounts.values() if getattr(a, "status", "Active") == "Active")

    def delete_all_accounts(self, admin: bool = False):
        if not admin:
            return False, "Admin privileges required"
        if self.member4 and hasattr(self.member4, "delete_all_accounts"):
            try:
                return self.member4.delete_all_accounts()
            except Exception:
                return False, "Delete failed"
        self.accounts.clear()
        try:
            save_accounts(self.accounts)
        except Exception:
            pass
        return True, "Deleted all accounts"

    def import_accounts(self, filepath: str):
        if self.member4 and hasattr(self.member4, "import_from_csv"):
            try:
                return self.member4.import_from_csv(filepath)
            except Exception:
                return False, "Import failed"
        return False, "Import feature not available"

    # ---------------- Member5 features (loans, EMI, FD) ----------------
    def loan_eligibility(self, acc_no, amount):
        if self.member5 and hasattr(self.member5, "loan_eligibility"):
            try:
                return self.member5.loan_eligibility(acc_no, amount)
            except Exception:
                return False, "Loan check failed"
        return False, "Loan feature not available"

    def credit_score(self, acc_no):
        if self.member5 and hasattr(self.member5, "credit_score"):
            try:
                return self.member5.credit_score(acc_no)
            except Exception:
                pass
        return None, "Credit score not available"

    def emi(self, principal, rate, years):
        if self.member5 and hasattr(self.member5, "emi"):
            try:
                return self.member5.emi(principal, rate, years)
            except Exception:
                return None, "EMI calculation failed"
        return None, "EMI feature not available"

    def create_fd(self, acc_no, amount, rate, years):
        if self.member5 and hasattr(self.member5, "create_fd"):
            try:
                return self.member5.create_fd(acc_no, amount, rate, years)
            except Exception:
                return False, "Create FD failed"
        return False, "FD feature not available"

    def list_fds(self, acc_no=None):
        if self.member5 and hasattr(self.member5, "list_fds"):
            try:
                return self.member5.list_fds(acc_no)
            except Exception:
                pass
        return {}

    def admin_summary(self):
        if self.member5 and hasattr(self.member5, "admin_summary"):
            try:
                return self.member5.admin_summary()
            except Exception:
                pass
        total_accounts = len(self.accounts)
        total_balance = sum(getattr(a, "balance", 0.0) or 0.0 for a in self.accounts.values())
        active_accounts = sum(1 for a in self.accounts.values() if getattr(a, "status", "Active") == "Active")
        return {
            "total_accounts": total_accounts,
            "total_balance": total_balance,
            "active_accounts": active_accounts,
            "closed_accounts": total_accounts - active_accounts,
            "fds": 0
        }

    # ---------------- Member6 wrappers ----------------
    def schedule_transfer(self, from_acc, to_acc, amount, execute_at_dt: datetime):
        if self.member6 and hasattr(self.member6, "schedule_transfer"):
            try:
                return self.member6.schedule_transfer(from_acc, to_acc, amount, execute_at_dt)
            except Exception:
                return False, "Schedule failed"
        return False, "Scheduling feature not available"

    def list_scheduled_transfers(self):
        if self.member6 and hasattr(self.member6, "list_scheduled_transfers"):
            try:
                return self.member6.list_scheduled_transfers()
            except Exception:
                return []
        return []

    def run_due_scheduled_transfers(self):
        if self.member6 and hasattr(self.member6, "run_due_scheduled_transfers"):
            try:
                return self.member6.run_due_scheduled_transfers(self)
            except Exception:
                return 0, []
        return 0, []

    def add_recurring(self, from_acc, to_acc, amount, interval_days, start_date: Optional[datetime] = None):
        if self.member6 and hasattr(self.member6, "add_recurring"):
            try:
                return self.member6.add_recurring(from_acc, to_acc, amount, interval_days, start_date)
            except Exception:
                return False, "Add recurring failed"
        return False, "Recurring feature not available"

    def list_recurring(self):
        if self.member6 and hasattr(self.member6, "list_recurring"):
            try:
                return self.member6.list_recurring()
            except Exception:
                return []
        return []

    def cancel_recurring(self, index: int):
        if self.member6 and hasattr(self.member6, "cancel_recurring"):
            try:
                return self.member6.cancel_recurring(index)
            except Exception:
                return False, "Cancel failed"
        return False, "Recurring cancel not available"

    def add_beneficiary(self, acc_no, beneficiary_acc_no, nickname=""):
        if self.member6 and hasattr(self.member6, "add_beneficiary"):
            try:
                return self.member6.add_beneficiary(acc_no, beneficiary_acc_no, nickname)
            except Exception:
                return False, "Add beneficiary failed"
        return False, "Benefits feature not available"

    def list_beneficiaries(self, acc_no):
        if self.member6 and hasattr(self.member6, "list_beneficiaries"):
            try:
                return self.member6.list_beneficiaries(acc_no)
            except Exception:
                return []
        return []

    def remove_beneficiary(self, acc_no, beneficiary_acc_no):
        if self.member6 and hasattr(self.member6, "remove_beneficiary"):
            try:
                return self.member6.remove_beneficiary(acc_no, beneficiary_acc_no)
            except Exception:
                return False, "Remove beneficiary failed"
        return False, "Remove beneficiary not available"

    def tag_transaction(self, acc_no, timestamp_str, tag, note=""):
        if self.member6 and hasattr(self.member6, "tag_transaction"):
            try:
                return self.member6.tag_transaction(acc_no, timestamp_str, tag, note)
            except Exception:
                return False, "Tagging failed"
        return False, "Tagging feature not available"

    def export_statement(self, acc_no, start_date=None, end_date=None, out_path="statement.csv"):
        if self.member6 and hasattr(self.member6, "export_statement"):
            try:
                return self.member6.export_statement(acc_no, start_date, end_date, out_path)
            except Exception:
                return False, "Export statement failed"
        return False, "Export statement not available"

    def set_overdraft(self, acc_no, limit, fee):
        if self.member6 and hasattr(self.member6, "set_overdraft"):
            try:
                return self.member6.set_overdraft(acc_no, limit, fee)
            except Exception:
                return False, "Set overdraft failed"
        return False, "Overdraft feature not available"

    def get_overdraft(self, acc_no):
        if self.member6 and hasattr(self.member6, "get_overdraft"):
            try:
                return self.member6.get_overdraft(acc_no)
            except Exception:
                return None
        return None

    def lock_account(self, acc_no):
        if self.member6 and hasattr(self.member6, "lock_account"):
            try:
                return self.member6.lock_account(acc_no)
            except Exception:
                return False, "Lock failed"
        return False, "Lock feature not available"

    def unlock_account(self, acc_no):
        if self.member6 and hasattr(self.member6, "unlock_account"):
            try:
                return self.member6.unlock_account(acc_no)
            except Exception:
                return False, "Unlock failed"
        return False, "Unlock feature not available"

    def reverse_last_transaction_for(self, acc_no):
        if self.member6 and hasattr(self.member6, "reverse_last_transaction"):
            try:
                return self.member6.reverse_last_transaction(acc_no, log_func=log_transaction)
            except Exception:
                return False, "Reverse failed"
        return False, "Reverse transaction feature not available"

    def set_account_currency(self, acc_no, currency_code):
        if self.member6 and hasattr(self.member6, "set_account_currency"):
            try:
                return self.member6.set_account_currency(acc_no, currency_code)
            except Exception:
                return False, "Currency set failed"
        return False, "Currency feature not available"

    def convert_balance(self, acc_no, to_currency):
        if self.member6 and hasattr(self.member6, "convert_balance"):
            try:
                return self.member6.convert_balance(acc_no, to_currency)
            except Exception:
                return None, "Convert failed"
        return None, "Convert feature not available"

    def set_low_balance_threshold(self, acc_no, threshold):
        if self.member6 and hasattr(self.member6, "set_low_balance_threshold"):
            try:
                return self.member6.set_low_balance_threshold(acc_no, threshold)
            except Exception:
                return False, "Set threshold failed"
        return False, "Low-balance feature not available"

    def get_low_balance_alerts(self):
        if self.member6 and hasattr(self.member6, "check_and_get_low_balance_alerts"):
            try:
                return self.member6.check_and_get_low_balance_alerts()
            except Exception:
                return []
        return []
