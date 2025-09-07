# src/main.py
from datetime import datetime
from services.banking_services import BankingService
from utils.file_manager import TRANSACTIONS_FILE

def print_account_row(a):
    try:
        print(f"{a.account_number} | {a.name} | Age:{int(a.age)} | {a.account_type} | ₹{float(a.balance):.2f} | {a.status}")
    except Exception:
        print(f"{getattr(a,'account_number', '')} | {getattr(a,'name','')} | Age:{getattr(a,'age','')} | {getattr(a,'account_type','')} | {getattr(a,'balance','')} | {getattr(a,'status','')}")

def print_accounts(accounts):
    if not accounts:
        print("No accounts.")
        return
    for a in accounts:
        print_account_row(a)

def main():
    bank = BankingService()
    print("Welcome — Global Digital Bank (Demo)")

    while True:
        print("\n=== MENU (features grouped) ===")
        print("1) Create account")
        print("2) Deposit (F6)")
        print("3) Withdraw (F6)")
        print("4) Balance inquiry / Search by account (F7)")
        print("5) Search by name (F1)")
        print("6) List active accounts (F2)")
        print("7) List closed accounts (F3)")
        print("8) Transfer funds (F11)")
        print("9) Transaction history (F12)")
        print("10) Upgrade account type (F4)")
        print("11) Reopen closed account (F5)")
        print("12) Simple interest calc (F9)")
        print("13) Average balance (F13)")
        print("14) Youngest / Oldest (F14/F15)")
        print("15) Top N accounts by balance (F16)")
        print("16) PIN set/check (F17)")
        print("17) Export accounts to CSV (F18)")
        print("18) Rename account holder (F20)")
        print("19) Count active accounts (F21)")
        print("20) Delete all accounts (ADMIN) (F22)")
        print("21) Import accounts from CSV (F24)")
        print("22) Loan eligibility (F25)")
        print("23) Credit score (F26)")
        print("24) EMI Calculator (F27)")
        print("25) Create Fixed Deposit (F28)")
        print("26) List Fixed Deposits (F28)")
        print("27) Notifications (F29)")
        print("28) Admin summary (F30)")
        # New features (F31-F40)
        print("29) Schedule transfer (F31)")
        print("30) List scheduled transfers (F31)")
        print("31) Run due scheduled/recurring tasks (F31+F33)")
        print("32) Add beneficiary (F32)")
        print("33) List beneficiaries (F32)")
        print("34) Remove beneficiary (F32)")
        print("35) Add recurring payment (F33)")
        print("36) List recurring payments (F33)")
        print("37) Cancel recurring payment (F33)")
        print("38) Tag a transaction (F34)")
        print("39) Export account statement CSV (F35)")
        print("40) Set overdraft (F36)")
        print("41) Lock / Unlock account (F37)")
        print("42) Reverse last transaction (F38)")
        print("43) Set account currency / convert (F39)")
        print("44) Set low-balance threshold / check alerts (F40)")
        print("0) Save & Exit (F23)")

        ch = input("Choose: ").strip()

        # ---------------- Basic features ----------------
        if ch == "1":
            name = input("Name: ")
            age = input("Age: ")
            acc_type = input("Type (Savings/Current): ")
            init = input("Initial deposit: ")
            acc, msg = bank.create_account(name, age, acc_type, init)
            # create_account returns (Account or None, message)
            print(msg)

        elif ch == "2":
            acc_no = input("Account #: ")
            amt = input("Amount: ")
            daily = input("Daily limit (press Enter to skip): ").strip()
            daily_limit = None
            if daily:
                try:
                    daily_limit = float(daily)
                except Exception:
                    print("Invalid daily limit - ignored.")
            ok, msg = bank.deposit(acc_no, amt, daily_limit)
            print(msg)

        elif ch == "3":
            acc_no = input("Account #: ")
            amt = input("Amount: ")
            daily = input("Daily limit (press Enter to skip): ").strip()
            daily_limit = None
            if daily:
                try:
                    daily_limit = float(daily)
                except Exception:
                    print("Invalid daily limit - ignored.")
            ok, msg = bank.withdraw(acc_no, amt, daily_limit)
            print(msg)

        elif ch == "4":
            acc_no = input("Enter account #: ").strip()
            try:
                acc = bank.accounts.get(int(acc_no))
            except Exception:
                acc = None
            if acc:
                print_account_row(acc)
            else:
                print("Not found")

        elif ch == "5":
            q = input("Name or part of name: ")
            if bank.member1 and hasattr(bank.member1, "search_by_name"):
                res = bank.member1.search_by_name(q)
                print_accounts(res if res else [])
            else:
                print("Search feature not available")

        elif ch == "6":
            if bank.member1 and hasattr(bank.member1, "list_active_accounts"):
                print_accounts(bank.member1.list_active_accounts())
            else:
                active = [a for a in bank.accounts.values() if a.status == "Active"]
                print_accounts(sorted(active, key=lambda x: x.account_number))

        elif ch == "7":
            if bank.member1 and hasattr(bank.member1, "list_closed_accounts"):
                print_accounts(bank.member1.list_closed_accounts())
            else:
                closed = [a for a in bank.accounts.values() if a.status != "Active"]
                print_accounts(sorted(closed, key=lambda x: x.account_number))

        elif ch == "8":
            src = input("From account #: ")
            dst = input("To account #: ")
            amt = input("Amount: ")
            ok, msg = bank.transfer(src, dst, amt)
            print(msg)

        elif ch == "9":
            acc_no = input("Account #: ").strip()
            res = bank.transaction_history(acc_no)
            if isinstance(res, tuple) and len(res) == 2:
                recs, msg = res
            else:
                recs, msg = res, "Transaction history"
            if recs:
                for r in recs:
                    print(f"{r.get('timestamp')} | {r.get('tx_id')} | {r.get('action')} | {r.get('amount')} | balance:{r.get('balance_after')} | note:{r.get('note')}")
            else:
                print(msg)

        elif ch == "10":
            acc_no = input("Account #: ")
            new_t = input("New type (Savings/Current): ")
            if bank.member1 and hasattr(bank.member1, "upgrade_account_type"):
                ok, msg = bank.member1.upgrade_account_type(acc_no, new_t)
                print(msg)
            else:
                print("Upgrade feature not available")

        elif ch == "11":
            acc_no = input("Account #: ")
            if bank.member1 and hasattr(bank.member1, "reopen_account"):
                ok, msg = bank.member1.reopen_account(acc_no)
                print(msg)
            else:
                print("Reopen feature not available")

        elif ch == "12":
            acc_no = input("Account #: ")
            rate = input("Rate (%): ")
            years = input("Years: ")
            res = bank.simple_interest(acc_no, rate, years)
            if isinstance(res, tuple) and len(res) == 2:
                val, msg = res
                print(msg)
            else:
                print(res)

        elif ch == "13":
            avg = bank.average_balance()
            print(f"Average balance across accounts: ₹{avg:.2f}")

        elif ch == "14":
            y = bank.youngest_account()
            o = bank.oldest_account()
            print("Youngest:")
            if y:
                print_account_row(y)
            else:
                print("None")
            print("Oldest:")
            if o:
                print_account_row(o)
            else:
                print("None")

        elif ch == "15":
            n = input("Top N (default 5): ").strip() or "5"
            try:
                top = bank.top_n_accounts(int(n))
            except Exception:
                top = bank.top_n_accounts(5)
            print_accounts(top)

        elif ch == "16":
            acc_no = input("Account #: ")
            action = input("Set (S) or Check (C)? ").strip().lower()
            if action == "s":
                pin = input("New PIN: ")
                ok, msg = bank.set_pin(acc_no, pin)
                print(msg)
            else:
                pin = input("PIN to check: ")
                ok, msg = bank.check_pin(acc_no, pin)
                print("PIN OK" if ok else "PIN incorrect or error")

        elif ch == "17":
            path = input("CSV path (e.g., accounts_export.csv): ").strip() or "accounts_export.csv"
            ok, msg = bank.export_accounts(path)
            print(msg)

        elif ch == "18":
            acc_no = input("Account #: ")
            newn = input("New name: ")
            ok, msg = bank.rename_account(acc_no, newn)
            print(msg)

        elif ch == "19":
            print("Active accounts:", bank.count_active_accounts())

        elif ch == "20":
            # Require admin password (stored hashed in data/admin.json)
            from utils.file_manager import get_admin_hash, set_admin_password, verify_admin_password
            if not get_admin_hash():
                print("No admin password set. Please create an admin password (min 6 chars).")
                pwd = input("New admin password: ").strip()
                confirm = input("Confirm admin password: ").strip()
                if pwd != confirm or len(pwd) < 6:
                    print("Passwords didn't match or too short. Admin action aborted.")
                    continue
                if not set_admin_password(pwd):
                    print("Failed to set admin password. Ensure bcrypt is installed.")
                    continue
                print("Admin password set. Please re-run the admin action and provide password.")
                continue

            pwd = input("Admin password: ").strip()
            if not verify_admin_password(pwd):
                print("Admin authentication failed.")
                continue

            ok, msg = bank.delete_all_accounts(admin=True)
            print(msg)

        elif ch == "21":
            path = input("CSV path to import: ")
            ok, msg = bank.import_accounts(path)
            print(msg)

        elif ch == "22":
            acc_no = input("Account #: ")
            amt = input("Requested loan amount: ")
            ok, msg = bank.loan_eligibility(acc_no, amt)
            print(msg)

        elif ch == "23":
            acc_no = input("Account #: ")
            score, msg = bank.credit_score(acc_no)
            print(msg)

        elif ch == "24":
            P = input("Principal: ")
            rate = input("Annual rate %: ")
            yrs = input("Years: ")
            emi_val, msg = bank.emi(P, rate, yrs)
            print(msg)

        elif ch == "25":
            acc_no = input("Account #: ")
            amt = input("Amount: ")
            rate = input("Rate %: ")
            yrs = input("Years: ")
            ok, msg = bank.create_fd(acc_no, amt, rate, yrs)
            print(msg)

        elif ch == "26":
            acc = input("Account # to list FDs for (enter to list all): ").strip()
            res = bank.list_fds(acc if acc else None)
            if res:
                for k, v in res.items():
                    print(k, v)
            else:
                print("No FDs")

        elif ch == "27":
            message = input("Notification message to push: ")
            if bank.member5 and hasattr(bank.member5, "push_notification"):
                bank.member5.push_notification(message)
            else:
                print("Notification push not available")

        elif ch == "28":
            print(bank.admin_summary())

        # ---------------- New features (F31-F40) ----------------
        elif ch == "29":
            src = input("From account #: ")
            dst = input("To account #: ")
            amt = input("Amount: ")
            dt_str = input("Execute at (YYYY-MM-DD HH:MM) or 'now': ")
            if dt_str.strip().lower() == "now":
                execute_at = datetime.now()
            else:
                try:
                    execute_at = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M")
                except Exception:
                    print("Invalid datetime format")
                    continue
            ok, msg = bank.schedule_transfer(src, dst, amt, execute_at)
            print(msg)

        elif ch == "30":
            for job in bank.list_scheduled_transfers():
                print(job)

        elif ch == "31":
            c1, executed = bank.run_due_scheduled_transfers()
            c2, rlogs = bank.run_due_recurring()
            print(f"Executed {c1} scheduled and {c2} recurring tasks")
            for l in executed + rlogs:
                print(l)

        elif ch == "32":
            acc = input("Your account #: "); ben = input("Beneficiary account #: "); nick = input("Nickname (opt): ")
            ok, msg = bank.add_beneficiary(acc, ben, nick)
            print(msg)

        elif ch == "33":
            acc = input("Account #: ")
            print(bank.list_beneficiaries(acc))

        elif ch == "34":
            acc = input("Account #: "); ben = input("Beneficiary acc #: ")
            ok, msg = bank.remove_beneficiary(acc, ben)
            print(msg)

        elif ch == "35":
            src = input("From acct #: "); dst = input("To acct #: ")
            amt = input("Amount: "); 
            try:
                interval = int(input("Interval days: "))
            except Exception:
                print("Invalid interval")
                continue
            ok, msg = bank.add_recurring(src, dst, amt, interval)
            print(msg)

        elif ch == "36":
            for i, job in enumerate(bank.list_recurring()):
                print(i, job)

        elif ch == "37":
            try:
                idx = int(input("Recurring index to cancel: "))
            except Exception:
                print("Invalid index")
                continue
            ok, msg = bank.cancel_recurring(idx)
            print(msg)

        elif ch == "38":
            acc = input("Account #: "); txid = input("Transaction tx_id to tag (copy from history): ")
            tag = input("Tag: "); note = input("Note (opt): ")
            ok, msg = bank.tag_transaction(acc, txid, tag, note)
            print(msg)

        elif ch == "39":
            acc = input("Account #: ")
            s = input("Start date (YYYY-MM-DD) or blank: ").strip()
            e = input("End date (YYYY-MM-DD) or blank: ").strip()
            start_dt = None
            end_dt = None
            if s:
                try:
                    start_dt = datetime.strptime(s, "%Y-%m-%d")
                except Exception:
                    print("Invalid start date")
                    continue
            if e:
                try:
                    end_dt = datetime.strptime(e, "%Y-%m-%d")
                except Exception:
                    print("Invalid end date")
                    continue
            out = input("Output CSV path (e.g., stmt.csv): ").strip() or f"statement_{acc}.csv"
            ok, msg = bank.export_statement(acc, start_dt, end_dt, out)
            print(msg)

        elif ch == "40":
            acc = input("Account #: ")
            try:
                lim = float(input("Overdraft limit (positive): "))
                fee = float(input("Fee on usage: "))
            except Exception:
                print("Invalid numeric input")
                continue
            ok, msg = bank.set_overdraft(acc, lim, fee)
            print(msg)

        elif ch == "41":
            sub = input("Lock (L) or Unlock (U)? ").strip().lower()
            acc = input("Account #: ")
            if sub == "l":
                ok, msg = bank.lock_account(acc)
            else:
                ok, msg = bank.unlock_account(acc)
            print(msg)

        elif ch == "42":
            acc = input("Account #: ")
            ok, msg = bank.reverse_last_transaction_for(acc)
            print(msg)

        elif ch == "43":
            acc = input("Account #: ")
            action = input("Set currency (S) or Convert view (C)? ").strip().lower()
            if action == "s":
                cur = input("Currency code (INR/USD/EUR/GBP): ").strip()
                ok, msg = bank.set_account_currency(acc, cur)
                print(msg)
            else:
                tocur = input("Convert to currency code: ").strip()
                val, msg = bank.convert_balance(acc, tocur)
                print(msg)

        elif ch == "44":
            sub = input("Set (S) threshold or Check (C)? ").strip().lower()
            if sub == "s":
                acc = input("Account #: ")
                try:
                    thr = float(input("Threshold amount: "))
                except Exception:
                    print("Invalid threshold")
                    continue
                ok, msg = bank.set_low_balance_threshold(acc, thr)
                print(msg)
            else:
                alerts = bank.get_low_balance_alerts()
                if alerts:
                    for a in alerts:
                        print(a)
                else:
                    print("No low-balance alerts")

        elif ch == "0":
            bank.save_to_disk()
            print("Saved. Goodbye.")
            break

        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
