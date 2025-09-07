# src/utils/file_manager.py
import csv
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from models.account import Account

# Build data dir relative to this file
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)

ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.csv")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.csv")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")

# ---------------- Accounts persistence ----------------
def load_accounts() -> Dict[int, Account]:
    accounts: Dict[int, Account] = {}
    if not os.path.exists(ACCOUNTS_FILE):
        return accounts
    try:
        with open(ACCOUNTS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    acc_no = int(row.get("account_number", 0) or 0)
                    acc = Account.from_dict({
                        "account_number": acc_no,
                        "name": row.get("name", "") or "",
                        "age": row.get("age", 0) or 0,
                        "account_type": row.get("account_type", "Savings") or "Savings",
                        "balance": row.get("balance", 0.0) or 0.0,
                        "status": row.get("status", "Active") or "Active",
                        "pin": row.get("pin", "") or None,
                        "created_at": row.get("created_at") or None
                    })
                    accounts[acc_no] = acc
                except Exception:
                    # skip malformed rows
                    continue
    except Exception:
        # If file can't be read, return empty dict
        return {}
    return accounts

def save_accounts(accounts: Dict[int, Account]) -> bool:
    """
    Persist accounts to ACCOUNTS_FILE. Returns True on success, False otherwise.
    """
    fieldnames = ["account_number", "name", "age", "account_type", "balance", "status", "pin", "created_at"]
    os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
    try:
        with open(ACCOUNTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for acc_no in sorted(accounts.keys()):
                acc = accounts[acc_no]
                row = acc.to_dict()
                # Ensure columns exist
                out = {
                    "account_number": int(row.get("account_number", acc_no)),
                    "name": row.get("name", ""),
                    "age": int(row.get("age", 0)),
                    "account_type": row.get("account_type", "Savings"),
                    "balance": row.get("balance", "0.00"),
                    "status": row.get("status", "Active"),
                    "pin": row.get("pin", "") or "",
                    "created_at": row.get("created_at", "")
                }
                writer.writerow(out)
        return True
    except Exception:
        return False

# ---------------- Transaction logging (robust CSV) ----------------
def _ensure_tx_file_has_header():
    if not os.path.exists(TRANSACTIONS_FILE):
        try:
            with open(TRANSACTIONS_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["tx_id", "timestamp", "account_number", "action", "amount", "balance_after", "note"])
        except Exception:
            pass

def log_transaction(account_number: int, action: str, amount: float, balance_after: float, note: str = "") -> None:
    """
    Append a transaction row to TRANSACTIONS_FILE with a unique tx_id and ISO timestamp.
    Fields: tx_id,timestamp,account_number,action,amount,balance_after,note
    """
    try:
        _ensure_tx_file_has_header()
        tx_id = str(uuid.uuid4())
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(TRANSACTIONS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([tx_id, ts, int(account_number), action, float(amount), float(balance_after), note or ""])
    except Exception:
        # do not raise — keep app running
        pass

# ---------------- Transaction read helpers ----------------
def read_transactions_for(account_number: int, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Returns most recent transaction rows for account as list of dicts (most-recent-first).
    """
    results: List[Dict[str, Any]] = []
    if not os.path.exists(TRANSACTIONS_FILE):
        return results
    try:
        with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        for row in reversed(reader):
            try:
                if str(row.get("account_number", "")).strip() == str(int(account_number)):
                    results.append(row)
                    if len(results) >= limit:
                        break
            except Exception:
                continue
    except Exception:
        pass
    return results

# alias for backward compatibility
read_transactions_for_account = read_transactions_for

# ---------------- Admin password helpers ----------------
def _read_admin_file() -> Dict[str, Any]:
    if not os.path.exists(ADMIN_FILE):
        return {}
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_admin_file(data: Dict[str, Any]) -> None:
    try:
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def get_admin_hash() -> str:
    data = _read_admin_file()
    return data.get("admin_password_hash", "")

def set_admin_password(plain_password: str) -> bool:
    try:
        import bcrypt as _bcrypt
    except Exception:
        return False
    if not plain_password or len(plain_password) < 6:
        return False
    try:
        hashed = _bcrypt.hashpw(plain_password.encode("utf-8"), _bcrypt.gensalt())
        _write_admin_file({"admin_password_hash": hashed.decode("utf-8")})
        return True
    except Exception:
        return False

def verify_admin_password(plain_password: str) -> bool:
    try:
        import bcrypt as _bcrypt
    except Exception:
        return False
    stored = get_admin_hash()
    if not stored:
        return False
    try:
        return _bcrypt.checkpw(plain_password.encode("utf-8"), stored.encode("utf-8"))
    except Exception:
        return False
