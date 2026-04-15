"""MISC module v3"""
from database.db import get_db

def post_misc_transaction(student_name, student_class, reference_no, payment_mode, amount, fee_type="MISC", receipt_no=""):
    conn = get_db()
    try:
        conn.execute("""INSERT INTO misc_transactions
            (student_name,class,reference_no,payment_mode,amount,fee_type,receipt_no)
            VALUES (?,?,?,?,?,?,?)""",
            (student_name,student_class,reference_no,payment_mode,amount,fee_type,receipt_no))
        conn.commit()
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def reverse_misc_transaction(receipt_no):
    conn = get_db()
    try:
        conn.execute("UPDATE misc_transactions SET status='cancelled' WHERE receipt_no=?", (receipt_no,))
        conn.commit()
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def get_misc_summary():
    """Overall summary: net_tuition + misc_to_pay vs what's been paid"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.student_name, s.reference_no, s.class, s.section,
                   COALESCE(s.student_uid,'') AS student_uid,
                   COALESCE(s.is_rte,0) AS is_rte,
                   COALESCE(s.gross_tuition,0) AS gross_tuition,
                   COALESCE(s.concession,0) AS concession,
                   COALESCE(s.net_tuition,0) AS net_tuition,
                   COALESCE(s.misc_to_pay,0) AS misc_to_pay,
                   COALESCE(s.neft_paid,0)+COALESCE(s.cash_paid,0) AS tuition_paid,
                   COALESCE((SELECT SUM(m.amount) FROM misc_transactions m
                              WHERE m.reference_no=s.reference_no AND m.status='active'),0) AS misc_paid
            FROM students s
            WHERE s.reference_no IS NOT NULL AND s.reference_no != ''
            ORDER BY CASE WHEN s.reference_no LIKE 'RA%' THEN 0 ELSE 1 END, s.reference_no""").fetchall()
        result = []
        for r in rows:
            net_tuition   = r["net_tuition"]
            misc_to_pay   = r["misc_to_pay"]
            tuition_paid  = r["tuition_paid"]
            misc_paid     = r["misc_paid"]
            total_payable = net_tuition + misc_to_pay
            total_paid    = tuition_paid + misc_paid
            balance       = total_payable - total_paid
            result.append({
                "student_name": r["student_name"],
                "reference_no": r["reference_no"],
                "class": r["class"] or "",
                "section": r["section"] or "",
                "student_uid": r["student_uid"] or "",
                "is_rte": r["is_rte"] or 0,
                "gross_tuition": r["gross_tuition"] or 0,
                "concession": r["concession"] or 0,
                "net_tuition": net_tuition,
                "misc_to_pay": misc_to_pay,
                "total_payable": total_payable,
                "tuition_paid": tuition_paid,
                "misc_paid": misc_paid,
                "total_paid": total_paid,
                "balance": balance,
            })
        return result
    finally:
        conn.close()

def get_misc_transactions():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT m.id, m.timestamp, m.student_name, m.class, m.reference_no,
                   m.payment_mode, m.amount, m.fee_type, m.receipt_no, m.status,
                   COALESCE(r.payment_date, '') AS payment_date
            FROM misc_transactions m
            LEFT JOIN receipt_log r ON r.receipt_no = m.receipt_no AND r.status='active'
            WHERE m.status='active'
            ORDER BY m.id ASC""").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_misc_to_pay(reference_no, amount, username="system"):
    conn = get_db()
    try:
        old_row = conn.execute("SELECT misc_to_pay, student_name FROM students WHERE reference_no=?", (reference_no,)).fetchone()
        conn.execute("UPDATE students SET misc_to_pay=?,updated_at=datetime('now','localtime') WHERE reference_no=?",
                     (amount, reference_no))
        # Log change for daily report
        if old_row and str(old_row["misc_to_pay"]) != str(amount):
            conn.execute("""INSERT INTO fee_change_log
                (reference_no, student_name, field_changed, old_value, new_value, changed_by)
                VALUES (?,?,?,?,?,?)""",
                (reference_no, old_row["student_name"], "misc_to_pay",
                 str(old_row["misc_to_pay"]), str(amount), username))
        conn.commit()
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()


def nuke_all_misc(password_provided):
    """Permanently destroy all MISC data. Requires password ANOVA. Irreversible."""
    if password_provided != "ANOVA":
        return {"success": False, "error": "Incorrect password"}
    import os, glob
    conn = get_db()
    try:
        # 1. Delete MISC PDF files from disk
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(db_path)))
        misc_pdf_dir = os.path.join(app_root, "receipts", "MISC")
        deleted_files = 0
        if os.path.isdir(misc_pdf_dir):
            for f in glob.glob(os.path.join(misc_pdf_dir, "*.pdf")):
                try:
                    os.remove(f)
                    deleted_files += 1
                except:
                    pass
            try:
                os.rmdir(misc_pdf_dir)
            except:
                pass

        # 2. Delete all MISC receipt_log rows
        misc_receipts = conn.execute("SELECT COUNT(*) FROM receipt_log WHERE fee_type='MISC'").fetchone()[0]
        conn.execute("DELETE FROM receipt_log WHERE fee_type='MISC'")

        # 3. Delete all cancelled receipts that were MISC
        conn.execute("DELETE FROM cancelled_receipts WHERE fee_type='MISC'")

        # 4. Drop misc_transactions table entirely
        conn.execute("DROP TABLE IF EXISTS misc_transactions")

        # 5. Zero out misc columns in students table
        conn.execute("UPDATE students SET misc_to_pay=0")

        # 6. Remove misc_receipt counter
        conn.execute("DELETE FROM counters WHERE name='misc_receipt'")

        # 7. Zero out misc_collected in daily_report_cache
        conn.execute("UPDATE daily_report_cache SET misc_collected=0")

        conn.commit()
        return {
            "success": True,
            "deleted_pdfs": deleted_files,
            "deleted_receipts": misc_receipts,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
