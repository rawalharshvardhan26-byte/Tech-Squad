from models.account import Account

class Member1Features:
    """
    Implements first 6 features:
    F1 - Search by Name
    F2 - List All Active Accounts
    F3 - List All Closed Accounts
    F4 - Account Type Upgrade
    F5 - Reopen Closed Account
    F6 - Transaction Log File (deposit/withdraw already logged in file_manager)
    """

    def __init__(self, accounts):
        # expects dict of account_number -> Account
        self.accounts = accounts

    # ---------- F1: Search by Name ----------
    def search_by_name(self, query):
        query = query.strip().lower()
        results = [acc for acc in self.accounts.values() if query in acc.name.lower()]
        return results if results else None

    # ---------- F2: List All Active Accounts ----------
    def list_active_accounts(self):
        return [acc for acc in self.accounts.values() if acc.status == "Active"]

    # ---------- F3: List All Closed Accounts ----------
    def list_closed_accounts(self):
        return [acc for acc in self.accounts.values() if acc.status != "Active"]

    # ---------- F4: Account Type Upgrade ----------
    def upgrade_account_type(self, account_number, new_type):
        acc = self.accounts.get(int(account_number))
        if not acc:
            return False, "Account not found"
        if acc.status != "Active":
            return False, "Account is not active. Reopen first."
        new_type = new_type.title()
        if new_type not in Account.MIN_BALANCE:
            return False, f"Invalid type. Choose from {list(Account.MIN_BALANCE.keys())}"
        if acc.account_type == new_type:
            return False, "Already of this type"
        old_type = acc.account_type
        acc.account_type = new_type
        return True, f"Account type changed from {old_type} → {new_type}"

    # ---------- F5: Reopen Closed Account ----------
    def reopen_account(self, account_number):
        acc = self.accounts.get(int(account_number))
        if not acc:
            return False, "Account not found"
        if acc.status == "Active":
            return False, "Account is already active"
        acc.status = "Active"
        return True, f"Account {account_number} reopened successfully"

    # ---------- F6: Deposit / Withdraw with Logging ----------
    # Note: deposit/withdraw already exist in Account + file_manager.log_transaction
    # Here we just wrap them
    def deposit(self, account_number, amount, log_func):
        acc = self.accounts.get(int(account_number))
        if not acc:
            return False, "Account not found"
        ok, msg = acc.deposit(amount)
        if ok:
            log_func(acc.account_number, "DEPOSIT", amount, acc.balance)
        return ok, msg

    def withdraw(self, account_number, amount, log_func):
        acc = self.accounts.get(int(account_number))
        if not acc:
            return False, "Account not found"
        ok, msg = acc.withdraw(amount)
        if ok:
            log_func(acc.account_number, "WITHDRAW", amount, acc.balance)
        return ok, msg