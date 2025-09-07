# src/models/account.py
"""
Account domain model used across the Global Digital Bank demo.

Responsibilities:
 - hold account data (number, name, age, type, balance, status, pin hash)
 - safely coerce inputs (defensive parsing)
 - PIN hashing/verification using bcrypt (fallback to plain-text if bcrypt missing)
 - deposit / withdraw helpers that return (ok, message)
 - simple serialization helpers (to_dict / from_dict)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import logging

# Try to import bcrypt; if not available, fall back (less secure).
try:
    import bcrypt
    _HAVE_BCRYPT = True
except Exception:
    bcrypt = None  # type: ignore
    _HAVE_BCRYPT = False

logger = logging.getLogger(__name__)


@dataclass
class Account:
    # class-level constants
    MIN_BALANCE = {"Savings": 500.0, "Current": 1000.0}
    MAX_SINGLE_DEPOSIT = 100_000.0

    # data fields
    account_number: int
    name: str
    age: int
    account_type: str = "Savings"
    balance: float = 0.0
    status: str = "Active"   # "Active" or "Inactive"
    pin: Optional[str] = None  # bcrypt hash string or plain (fallback)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def __post_init__(self):
        # Defensive coercion of fields
        try:
            self.account_number = int(self.account_number)
        except Exception:
            raise ValueError(f"Invalid account_number: {self.account_number}")

        self.name = (self.name or "").strip()

        try:
            self.age = int(self.age)
        except Exception:
            self.age = 0

        # Normalize account type and ensure valid
        self.account_type = (self.account_type or "Savings").title()
        if self.account_type not in Account.MIN_BALANCE:
            self.account_type = "Savings"

        # Normalize balance
        try:
            if isinstance(self.balance, str):
                b = self.balance.replace("₹", "").replace(",", "").strip()
            else:
                b = self.balance
            self.balance = float(b)
        except Exception:
            self.balance = 0.0

        # Normalize status to Active / Inactive
        norm_status = (self.status or "Active").strip().title()
        self.status = "Active" if norm_status == "Active" else "Inactive"

        # If a plain-text PIN was provided, hash it; if looks like bcrypt hash keep it
        if self.pin:
            if isinstance(self.pin, str) and self.pin.startswith("$2") and _HAVE_BCRYPT:
                # assume bcrypt hash provided
                self.pin = self.pin
            elif isinstance(self.pin, str) and not _HAVE_BCRYPT:
                # bcrypt not available; keep provided value but log a warning
                logger.warning("bcrypt not available — storing PIN value as plain text (insecure). Install 'bcrypt' package to enable hashing.")
            elif isinstance(self.pin, str):
                # plain PIN string — hash it
                try:
                    self.pin = self._hash_pin(str(self.pin))
                except Exception:
                    # fallback: keep plain but log
                    logger.exception("Failed to hash PIN; storing plain PIN as fallback.")
            else:
                # any other type -> stringify then hash if possible
                try:
                    self.pin = self._hash_pin(str(self.pin))
                except Exception:
                    self.pin = str(self.pin)

    # ---------------- PIN helpers ----------------
    def _hash_pin(self, plain_pin: str) -> str:
        """Return bcrypt hash for a plaintext PIN (or plain string fallback)."""
        if not _HAVE_BCRYPT:
            # fallback: not secure
            logger.warning("bcrypt not installed; PIN will be stored as plain text (insecure).")
            return str(plain_pin)
        try:
            pb = plain_pin.encode("utf-8") if not isinstance(plain_pin, bytes) else plain_pin
            hashed = bcrypt.hashpw(pb, bcrypt.gensalt())
            return hashed.decode("utf-8")
        except Exception as e:
            logger.exception("bcrypt hashing failed")
            raise

    def set_pin(self, plain_pin: str) -> Tuple[bool, str]:
        """Set (or replace) the account PIN. Returns (ok, message)."""
        try:
            plain_pin = str(plain_pin)
            if not plain_pin or len(plain_pin) < 4:
                return False, "PIN must be at least 4 characters"
            self.pin = self._hash_pin(plain_pin)
            return True, "PIN set"
        except Exception as e:
            logger.exception("set_pin failed")
            return False, f"Failed to set PIN: {e}"

    def check_pin(self, attempt: str) -> bool:
        """Verify a plaintext PIN attempt against the stored bcrypt hash. Returns True/False."""
        try:
            if not self.pin:
                return False
            attempt = str(attempt)
            if _HAVE_BCRYPT and isinstance(self.pin, str) and self.pin.startswith("$2"):
                return bcrypt.checkpw(attempt.encode("utf-8"), self.pin.encode("utf-8"))
            # fallback: plain-text compare (insecure)
            return str(self.pin) == attempt
        except Exception:
            logger.exception("check_pin failed")
            return False

    # ---------------- Basic helpers ----------------
    def is_active(self) -> bool:
        """Return True if account status is Active."""
        return str(self.status).lower() == "active"

    def deposit(self, amount) -> Tuple[bool, str]:
        """Deposit amount into account. Returns (ok, message)."""
        try:
            if isinstance(amount, str):
                amt = float(str(amount).replace("₹", "").replace(",", "").strip())
            else:
                amt = float(amount)
        except Exception:
            return False, "Invalid deposit amount"

        if amt <= 0:
            return False, "Deposit amount must be positive"

        if amt > Account.MAX_SINGLE_DEPOSIT:
            return False, f"Deposit exceeds single-transaction cap of ₹{Account.MAX_SINGLE_DEPOSIT:.2f}"

        if not self.is_active():
            return False, "Account is not active"

        before = self.balance
        self.balance += amt
        return True, f"Deposited ₹{amt:.2f}. Balance: ₹{self.balance:.2f} (before: ₹{before:.2f})"

    def withdraw(self, amount) -> Tuple[bool, str]:
        """
        Withdraw amount from account. This method enforces minimum-balance rules
        based on account type (so callers don't need to duplicate the check).
        Returns (ok, message).
        """
        try:
            if isinstance(amount, str):
                amt = float(str(amount).replace("₹", "").replace(",", "").strip())
            else:
                amt = float(amount)
        except Exception:
            return False, "Invalid withdrawal amount"

        if amt <= 0:
            return False, "Withdrawal amount must be positive"

        if not self.is_active():
            return False, "Account is not active"

        min_required = Account.MIN_BALANCE.get(self.account_type, 0.0)
        remaining = self.balance - amt

        if remaining < min_required:
            return False, f"Insufficient funds. Minimum required balance for {self.account_type}: ₹{min_required:.2f} (would remain ₹{remaining:.2f})"

        before = self.balance
        self.balance -= amt
        return True, f"Withdrew ₹{amt:.2f}. Balance: ₹{self.balance:.2f} (before: ₹{before:.2f})"

    def transfer_to(self, other: "Account", amount) -> Tuple[bool, str]:
        """
        Transfer amount to another account. Attempts to withdraw from self and deposit into other.
        Returns (ok, message).
        """
        if not isinstance(other, Account):
            return False, "Recipient account invalid"

        if not self.is_active():
            return False, "Sender account is not active"

        if not other.is_active():
            return False, "Recipient account is not active"

        # attempt withdrawal from sender
        ok, msg = self.withdraw(amount)
        if not ok:
            return False, f"Transfer failed: {msg}"

        # deposit into recipient
        ok2, msg2 = other.deposit(amount)
        if not ok2:
            # rollback sender withdrawal
            try:
                self.balance += float(amount)
            except Exception:
                logger.exception("rollback failed after transfer deposit failure")
            return False, f"Transfer failed: {msg2} (sender rolled back)"

        return True, f"Transfer successful. Sender balance: ₹{self.balance:.2f}; Recipient balance: ₹{other.balance:.2f}"

    def apply_overdraft_fee(self, fee_amount: float) -> Tuple[bool, str]:
        """Apply overdraft fee by subtracting fee_amount from balance (can go negative)."""
        try:
            fee = float(fee_amount)
        except Exception:
            return False, "Invalid fee amount"

        self.balance -= fee
        return True, f"Overdraft fee applied: ₹{fee:.2f}. New balance: ₹{self.balance:.2f}"

    # ---------------- Serialization ----------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize account to dict (suitable for CSV writing)."""
        return {
            "account_number": int(self.account_number),
            "name": self.name,
            "age": int(self.age),
            "balance": f"{self.balance:.2f}",
            "account_type": self.account_type,
            "status": self.status,
            "pin": self.pin or "",
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        """Create Account instance from dict (CSV row)."""
        return cls(
            account_number=int(data.get("account_number", 0)),
            name=data.get("name", "") or "",
            age=int(data.get("age", 0) or 0),
            account_type=data.get("account_type", "Savings") or "Savings",
            balance=float(data.get("balance", 0.0) or 0.0),
            status=(data.get("status", "Active") or "Active"),
            pin=(data.get("pin") or None),
            created_at=(data.get("created_at") or datetime.now().isoformat(timespec="seconds"))
        )

    def __str__(self) -> str:
        return f"[{self.account_number}] {self.name} | Type: {self.account_type} | Balance: ₹{self.balance:.2f} | Status: {self.status}"
