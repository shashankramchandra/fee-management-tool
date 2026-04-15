"""Receipts module v2 - with cancellation support"""
from database.db import get_db
from modules.admissions import generate_receipt_no
from modules.students import post_tuition_payment
from modules.misc import post_misc_transaction, reverse_misc_transaction
from modules.utils import rupees_in_words
from modules.pdf_generator import generate_receipt_pdf, generate_cancellation_pdf
from modules.auth import audit

def generate_receipt(data, username="system"):
    errors = []
    for f,lbl in [("student_name","Student Name"),("parent_name","Parent Name"),
                  ("grade","Grade"),("payment_mode","Payment Mode"),
                  ("fee_type","Fee Type"),("reference_no","Reference Number"),
                  ("payment_date","Payment Date")]:
        if not data.get(f,"").strip(): errors.append(f"{lbl} is missing")
    if not data.get("amount") or float(data.get("amount",0))<=0:
        errors.append("Amount must be greater than 0")
    if errors: return {"success":False,"errors":errors}

    fee_type = "TUITION" if "TUITION" in data["fee_type"].upper() else "MISC"
    amount = float(data["amount"])
    payment_mode = data["payment_mode"].upper()

    receipt_result = generate_receipt_no(fee_type)
    if not receipt_result["success"]: return {"success":False,"errors":[receipt_result["error"]]}
    receipt_no = receipt_result["receipt_no"]

    if fee_type=="TUITION":
        post_result = post_tuition_payment(
            data["student_name"], data.get("father_name",data.get("parent_name","")),
            data.get("mother_name",""), amount, payment_mode)
    else:
        post_result = post_misc_transaction(
            data["student_name"], data.get("grade",""), data["reference_no"],
            payment_mode, amount, "MISC", receipt_no)
    if not post_result["success"]: return {"success":False,"errors":[post_result["error"]]}

    pdf_data = {k:data.get(k,"") for k in ["student_name","parent_name","grade","section","payment_mode","payment_date","reference_no","fee_type"]}
    pdf_data["receipt_no"] = receipt_no
    pdf_data["amount"] = amount
    pdf_data["amount_words"] = rupees_in_words(amount)
    pdf_result = generate_receipt_pdf(pdf_data, fee_type)

    _log_receipt(receipt_no, data, amount, payment_mode, fee_type, pdf_result.get("pdf_path",""), username)
    audit(username,"admin","GENERATE_RECEIPT",
          f"Receipt:{receipt_no} Student:{data['student_name']} Amount:{amount} Type:{fee_type}")
    return {"success":True,"receipt_no":receipt_no,"amount_words":rupees_in_words(amount),
            "pdf_filename":pdf_result.get("pdf_filename",""),"message":f"Receipt {receipt_no} generated!"}

def cancel_receipt(receipt_no, reason, username="system"):
    conn = get_db()
    try:
        r = conn.execute("SELECT * FROM receipt_log WHERE receipt_no=? AND status='active'", (receipt_no,)).fetchone()
        if not r: return {"success":False,"error":"Receipt not found or already cancelled"}
        r = dict(r)

        # Reverse the payment
        student = conn.execute("SELECT * FROM students WHERE student_name=?", (r["student_name"],)).fetchone()
        if student and r["fee_type"]=="TUITION":
            col = "neft_paid" if r["payment_mode"]=="NEFT" else "cash_paid"
            conn.execute(f"UPDATE students SET {col}=COALESCE({col},0)-?,updated_at=datetime('now','localtime') WHERE student_name=?",
                         (r["amount"], r["student_name"]))
        elif r["fee_type"]=="MISC":
            conn.execute("UPDATE misc_transactions SET status='cancelled' WHERE receipt_no=?", (receipt_no,))

        # Mark as cancelled
        conn.execute("UPDATE receipt_log SET status='cancelled' WHERE receipt_no=?", (receipt_no,))

        # Log cancellation
        conn.execute("""INSERT INTO cancelled_receipts
            (original_receipt_no,student_name,amount,fee_type,payment_mode,reason,cancelled_by)
            VALUES (?,?,?,?,?,?,?)""",
            (receipt_no, r["student_name"], r["amount"], r["fee_type"],
             r["payment_mode"], reason, username))

        conn.commit()

        # Generate cancellation PDF
        pdf_result = generate_cancellation_pdf(r, reason, username)
        if pdf_result.get("pdf_path"):
            conn2 = get_db()
            conn2.execute("UPDATE cancelled_receipts SET cancellation_pdf=? WHERE original_receipt_no=?",
                          (pdf_result["pdf_path"], receipt_no))
            conn2.commit()
            conn2.close()

        audit(username,"admin","CANCEL_RECEIPT",
              f"Cancelled:{receipt_no} Student:{r['student_name']} Reason:{reason}")
        return {"success":True,"message":f"Receipt {receipt_no} cancelled",
                "cancellation_pdf":pdf_result.get("pdf_filename","")}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def search_receipts(query):
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT receipt_no,student_name,amount,fee_type,payment_mode,payment_date,status,created_by,created_at
               FROM receipt_log
               WHERE (receipt_no LIKE ? OR student_name LIKE ?) AND status='active'
               ORDER BY created_at DESC LIMIT 20""",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_cancelled_receipts():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM cancelled_receipts ORDER BY cancelled_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def _log_receipt(receipt_no, data, amount, payment_mode, fee_type, pdf_path, username):
    conn = get_db()
    try:
        conn.execute("""INSERT OR IGNORE INTO receipt_log
            (receipt_no,student_name,parent_name,grade,section,reference_no,
             amount,payment_mode,payment_date,fee_type,pdf_path,created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (receipt_no, data.get("student_name",""), data.get("parent_name",""),
             data.get("grade",""), data.get("section",""), data.get("reference_no",""),
             amount, payment_mode, data.get("payment_date",""), fee_type, pdf_path, username))
        conn.commit()
    finally:
        conn.close()

def get_receipt_log(page=1, per_page=50, fee_type=""):
    conn = get_db()
    try:
        where = "WHERE fee_type=? AND status='active'" if fee_type else "WHERE status='active'"
        params = [fee_type] if fee_type else []
        total = conn.execute(f"SELECT COUNT(*) FROM receipt_log {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM receipt_log {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params+[per_page,(page-1)*per_page]
        ).fetchall()
        return {"total":total,"page":page,"per_page":per_page,"receipts":[dict(r) for r in rows]}
    finally:
        conn.close()

def get_receipt_counts():
    conn = get_db()
    try:
        rows = conn.execute("SELECT name,value FROM counters").fetchall()
        return {r["name"]:r["value"] for r in rows}
    finally:
        conn.close()
