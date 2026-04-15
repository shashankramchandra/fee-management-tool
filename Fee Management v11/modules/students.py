"""Students module v3"""
from database.db import get_db
from modules.admissions import get_next_ref_no, get_next_readmission_no
from modules.auth import audit
from datetime import datetime

def search_students(query, field="student", no_ref_only=False):
    if not query and not no_ref_only: return []
    conn = get_db()
    try:
        col = {"student":"student_name","father":"father_name","mother":"mother_name"}.get(field,"student_name")
        if no_ref_only:
            where = f"WHERE (reference_no IS NULL OR reference_no='') AND {col} LIKE ?"
        else:
            where = f"WHERE {col} LIKE ?"
        rows = conn.execute(
            f"""SELECT id,student_name,father_name,mother_name,class,section,
                       reference_no,status,father_contact,mother_contact,
                       gross_tuition,net_tuition,misc_to_pay,neft_paid,cash_paid
                FROM students {where} ORDER BY student_name LIMIT 40""",
            (f"%{query}%",)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_all_students():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id,date_of_admission,sl_no,student_name,class,section,
                      reference_no,father_name,mother_name,father_contact,mother_contact,
                      status,gross_tuition,concession,net_tuition,misc_to_pay,
                      neft_paid,cash_paid,balance,comments,student_uid,is_rte
               FROM students ORDER BY
               CASE WHEN reference_no LIKE 'RA%' THEN 0
                    WHEN reference_no LIKE 'NA%' THEN 1
                    ELSE 2 END, reference_no"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_students_no_ref():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id,student_name,father_name,mother_name,class,section,
                      father_contact,mother_contact,gross_tuition,net_tuition,misc_to_pay
               FROM students WHERE reference_no IS NULL OR reference_no=''
               ORDER BY student_name"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_student_by_ref(ref_no):
    conn = get_db()
    try:
        r = conn.execute("SELECT * FROM students WHERE reference_no=?", (ref_no,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()

def get_student_by_names(student_name, father_name, mother_name):
    conn = get_db()
    try:
        r = conn.execute(
            "SELECT * FROM students WHERE student_name=? AND father_name=? AND mother_name=?",
            (student_name, father_name, mother_name)
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()

def add_student(data, admission_type="NA", username="system"):
    required = ["student_name","father_name","mother_name","grade"]
    for f in required:
        if not str(data.get(f,"")).strip():
            return {"success":False,"error":f"{f.replace('_',' ').title()} is required"}
    conn = get_db()
    try:
        existing = conn.execute(
            """SELECT id FROM students
               WHERE LOWER(TRIM(student_name))=LOWER(TRIM(?))
               AND LOWER(TRIM(father_name))=LOWER(TRIM(?))
               AND LOWER(TRIM(mother_name))=LOWER(TRIM(?))""",
            (data["student_name"],data["father_name"],data["mother_name"])
        ).fetchone()
        if existing:
            return {"success":False,"error":"Student with same name/parents already exists"}

        if admission_type == "RA":
            ref_result = get_next_readmission_no()
        else:
            ref_result = get_next_ref_no()
        if not ref_result["success"]: return ref_result
        ref_no = ref_result["ref_no"]

        max_sl = conn.execute("SELECT MAX(sl_no) FROM students").fetchone()[0]
        sl_no = (max_sl or 0) + 1
        gross = float(data.get("gross_tuition",0) or 0)
        conc  = float(data.get("concession",0) or 0)
        net   = float(data.get("net_tuition", gross - conc) or (gross - conc))

        conn.execute("""INSERT INTO students
            (date_of_admission,sl_no,student_name,class,section,reference_no,
             father_name,mother_name,father_contact,mother_contact,status,
             gross_tuition,concession,net_tuition,misc_to_pay,comments)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("date_of_admission", str(datetime.now().day) + datetime.now().strftime("-%b-%Y")),
             sl_no, data["student_name"].strip(), data["grade"].strip(),
             data.get("section","").strip(), ref_no,
             data["father_name"].strip(), data["mother_name"].strip(),
             data.get("father_contact","").strip(), data.get("mother_contact","").strip(),
             "Admitted", gross, conc, net,
             float(data.get("misc_to_pay",0) or 0),
             data.get("comments","").strip()))
        conn.commit()
        audit(username,"admin",f"ADD_STUDENT_{admission_type}",
              f"Added: {data['student_name']} ref:{ref_no}")
        return {"success":True,"ref_no":ref_no,"sl_no":sl_no}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def assign_ref_to_existing(student_id, admission_type, data, username="system"):
    """Assign RA/NA ref to an existing student (no-ref student)"""
    # Validate mandatory fields
    for field, label in [("father_name","Father Name"),("mother_name","Mother Name"),
                          ("gross_tuition","Gross Tuition Fee"),("misc_to_pay","MISC to Pay")]:
        v = data.get(field)
        if v is None or str(v).strip() == "" or (field in ("gross_tuition","misc_to_pay") and float(v or 0)==0):
            return {"success":False,"error":f"{label} is required before admission number can be assigned."}

    conn = get_db()
    try:
        student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if not student:
            return {"success":False,"error":"Student not found"}
        if student["reference_no"]:
            return {"success":False,"error":f"Student already has reference: {student['reference_no']}"}

        if admission_type == "RA":
            ref_result = get_next_readmission_no()
        else:
            ref_result = get_next_ref_no()
        if not ref_result["success"]: return ref_result
        ref_no = ref_result["ref_no"]

        gross   = float(data.get("gross_tuition", student["gross_tuition"] or 0) or 0)
        conc    = float(data.get("concession", student["concession"] or 0) or 0)
        net     = gross - conc
        is_rte  = 1 if data.get("is_rte") else 0

        # Generate UID if student doesn't have one
        uid = student["student_uid"] if (student["student_uid"] if "student_uid" in student.keys() else None) else None
        if not uid:
            import random, string
            doa = data.get("date_of_admission","")
            year_prefix = "26" if "2026" in doa else "25"
            existing = set(r[0] for r in conn.execute("SELECT student_uid FROM students WHERE student_uid IS NOT NULL AND student_uid!=''").fetchall())
            for _ in range(10000):
                letters = ''.join(random.choices(string.ascii_uppercase, k=3))
                candidate = f"{year_prefix}{letters}"
                if candidate not in existing:
                    uid = candidate
                    break

        conn.execute("""UPDATE students SET
            reference_no=?, status='Admitted',
            class=COALESCE(NULLIF(?,''),(class)),
            section=COALESCE(NULLIF(?,''),(section)),
            father_name=COALESCE(NULLIF(?,''),(father_name)),
            mother_name=COALESCE(NULLIF(?,''),(mother_name)),
            father_contact=COALESCE(NULLIF(?,''),(father_contact)),
            mother_contact=COALESCE(NULLIF(?,''),(mother_contact)),
            gross_tuition=?, concession=?, net_tuition=?,
            balance=?-COALESCE(neft_paid,0)-COALESCE(cash_paid,0),
            misc_to_pay=?,
            date_of_admission=?,
            student_uid=COALESCE(NULLIF(?,''),student_uid),
            is_rte=?,
            updated_at=datetime('now','localtime')
            WHERE id=?""",
            (ref_no,
             data.get("grade",""), data.get("section",""),
             data.get("father_name",""), data.get("mother_name",""),
             data.get("father_contact",""), data.get("mother_contact",""),
             gross, conc, net, net,
             float(data.get("misc_to_pay",0) or 0),
             data.get("date_of_admission", str(datetime.now().day)+datetime.now().strftime("-%b-%Y")),
             uid or "", is_rte,
             student_id))
        conn.commit()
        audit(username,"admin",f"ASSIGN_REF_{admission_type}",
              f"Assigned {ref_no} to student id:{student_id} name:{student['student_name']}")
        return {"success":True,"ref_no":ref_no,"student_uid":uid}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def update_student_field(student_id, field, value, username="system"):
    allowed = ["student_name","father_name","mother_name","class","section",
               "father_contact","mother_contact","status","gross_tuition",
               "concession","net_tuition","misc_to_pay","comments","date_of_admission"]
    if field not in allowed:
        return {"success":False,"error":"Field not editable"}
    conn = get_db()
    try:
        old = conn.execute(f"SELECT {field} FROM students WHERE id=?", (student_id,)).fetchone()
        old_val = old[0] if old else "?"
        conn.execute(f"UPDATE students SET {field}=?, updated_at=datetime('now','localtime') WHERE id=?",
                     (value, student_id))
        # Recalculate net if gross/concession changed
        if field in ["gross_tuition","concession"]:
            conn.execute("""UPDATE students SET
                net_tuition = COALESCE(gross_tuition,0) - COALESCE(concession,0),
                balance = COALESCE(gross_tuition,0) - COALESCE(concession,0) - COALESCE(neft_paid,0) - COALESCE(cash_paid,0),
                updated_at = datetime('now','localtime') WHERE id=?""", (student_id,))
        # Log fee-affecting changes to fee_change_log for daily report
        if field in ["gross_tuition","concession","net_tuition","misc_to_pay"]:
            s = conn.execute("SELECT student_name, reference_no FROM students WHERE id=?", (student_id,)).fetchone()
            if s:
                conn.execute("""INSERT INTO fee_change_log
                    (reference_no, student_name, field_changed, old_value, new_value, changed_by)
                    VALUES (?,?,?,?,?,?)""",
                    (s["reference_no"], s["student_name"], field, str(old_val), str(value), username))
        conn.commit()
        audit(username,"management","EDIT_STUDENT",
              f"id:{student_id} field:{field} '{old_val}'->'{value}'")
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def update_tuition_fees(student_id, gross, concession, username="system"):
    """Update gross/concession/net together"""
    conn = get_db()
    try:
        net = float(gross) - float(concession)
        old_row = conn.execute("SELECT gross_tuition, concession, student_name, reference_no FROM students WHERE id=?", (student_id,)).fetchone()
        conn.execute("""UPDATE students SET gross_tuition=?, concession=?, net_tuition=?,
                        balance=?-COALESCE(neft_paid,0)-COALESCE(cash_paid,0),
                        updated_at=datetime('now','localtime') WHERE id=?""",
                     (gross, concession, net, net, student_id))
        # Log to fee_change_log
        if old_row:
            for field, old_v, new_v in [("gross_tuition", old_row["gross_tuition"], gross),
                                         ("concession", old_row["concession"], concession)]:
                if str(old_v) != str(new_v):
                    conn.execute("""INSERT INTO fee_change_log
                        (reference_no, student_name, field_changed, old_value, new_value, changed_by)
                        VALUES (?,?,?,?,?,?)""",
                        (old_row["reference_no"], old_row["student_name"], field, str(old_v), str(new_v), username))
        conn.commit()
        audit(username,"management","UPDATE_TUITION_FEES",
              f"id:{student_id} gross:{gross} conc:{concession} net:{net}")
        return {"success":True,"net":net}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def update_phone(student_id, father_contact, mother_contact, username="system"):
    conn = get_db()
    try:
        conn.execute("""UPDATE students SET father_contact=?,mother_contact=?,
                        updated_at=datetime('now','localtime') WHERE id=?""",
                     (father_contact, mother_contact, student_id))
        conn.commit()
        audit(username,"admin","UPDATE_PHONE",f"Updated phone id:{student_id}")
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def post_tuition_payment(student_name, father_name, mother_name, amount, payment_mode):
    col = "neft_paid" if payment_mode.upper()=="NEFT" else "cash_paid"
    conn = get_db()
    try:
        conn.execute(f"""UPDATE students SET 
                        {col}=COALESCE({col},0)+?,
                        updated_at=datetime('now','localtime')
                        WHERE student_name=? AND father_name=? AND mother_name=?""",
                     (amount, student_name, father_name, mother_name))
        # Recalculate balance cleanly: net_tuition - total paid
        conn.execute("""UPDATE students SET
                        balance=COALESCE(net_tuition,0)-COALESCE(neft_paid,0)-COALESCE(cash_paid,0)
                        WHERE student_name=? AND father_name=? AND mother_name=?""",
                     (student_name, father_name, mother_name))
        conn.commit()
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def reverse_tuition_payment(student_name, father_name, mother_name, amount, payment_mode):
    col = "neft_paid" if payment_mode.upper()=="NEFT" else "cash_paid"
    conn = get_db()
    try:
        conn.execute(f"""UPDATE students SET
                        {col}=COALESCE({col},0)-?,
                        balance=COALESCE(net_tuition,0) - (COALESCE(neft_paid,0)-?) - COALESCE(cash_paid,0),
                        updated_at=datetime('now','localtime')
                        WHERE student_name=? AND father_name=? AND mother_name=?""",
                     (amount, amount, student_name, father_name, mother_name))
        # Recalculate cleanly after reverse
        conn.execute("""UPDATE students SET 
                        balance=COALESCE(net_tuition,0)-COALESCE(neft_paid,0)-COALESCE(cash_paid,0)
                        WHERE student_name=?""", (student_name,))
        conn.commit()
        return {"success":True}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def delete_student(student_name, reason="TC", username="system"):
    if not student_name: return {"success":False,"error":"Student name required"}
    conn = get_db()
    try:
        # Check no active receipts
        active = conn.execute("""SELECT COUNT(*) FROM receipt_log 
                                 WHERE student_name=? AND status='active'""",
                              (student_name,)).fetchone()[0]
        if active > 0:
            return {"success":False,
                    "error":f"This student has {active} active receipt(s). Please cancel all receipts first before issuing TC."}
        s = conn.execute("SELECT * FROM students WHERE student_name=?", (student_name,)).fetchone()
        if not s: return {"success":False,"error":"Student not found"}
        s = dict(s)
        conn.execute("""INSERT INTO deleted_students
            (student_name,reference_no,father_name,mother_name,deleted_reason,deleted_by)
            VALUES (?,?,?,?,?,?)""",
            (s["student_name"],s["reference_no"],s["father_name"],s["mother_name"],reason,username))
        conn.execute("DELETE FROM students WHERE student_name=?", (student_name,))
        conn.commit()
        audit(username,"admin","DELETE_STUDENT",
              f"Deleted: {student_name} ref:{s['reference_no']} reason:{reason}")
        return {"success":True,"message":f"Student '{student_name}' deleted"}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()
