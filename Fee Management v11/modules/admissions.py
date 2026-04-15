"""Admissions module v3"""
from database.db import get_db
from datetime import datetime
import random, string

def get_next_ref_no():
    conn = get_db()
    try:
        conn.execute("UPDATE counters SET value=value+1 WHERE name='new_admission'")
        row = conn.execute("SELECT value FROM counters WHERE name='new_admission'").fetchone()
        conn.commit()
        return {"success":True,"ref_no":f"NA{row['value']:03d}"}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def get_next_readmission_no():
    conn = get_db()
    try:
        conn.execute("UPDATE counters SET value=value+1 WHERE name='re_admission'")
        row = conn.execute("SELECT value FROM counters WHERE name='re_admission'").fetchone()
        conn.commit()
        return {"success":True,"ref_no":f"RA{row['value']:03d}"}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def _rand_prefix():
    return ''.join(random.choices(string.ascii_uppercase,k=3)) + ''.join(random.choices(string.digits,k=3))

def generate_receipt_no(fee_type):
    counter_name = {"TUITION":"tuition_receipt","MISC":"misc_receipt"}.get(fee_type.upper())
    type_char    = {"TUITION":"T","MISC":"M"}.get(fee_type.upper())
    if not counter_name:
        return {"success":False,"error":f"Invalid fee type: {fee_type}"}
    conn = get_db()
    try:
        conn.execute("UPDATE counters SET value=value+1 WHERE name=?", (counter_name,))
        row = conn.execute("SELECT value FROM counters WHERE name=?", (counter_name,)).fetchone()
        next_no = row["value"]
        prefix = None
        for _ in range(1000):
            cand = _rand_prefix()
            if not conn.execute("SELECT 1 FROM used_prefixes WHERE prefix=?", (cand,)).fetchone():
                conn.execute("INSERT INTO used_prefixes (prefix) VALUES (?)", (cand,))
                prefix = cand
                break
        if not prefix:
            conn.rollback()
            return {"success":False,"error":"Could not generate unique prefix"}
        conn.commit()
        return {"success":True,"receipt_no":f"{prefix}-{type_char}-{next_no:06d}"}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def _generate_uid(year_prefix, conn):
    existing = set(r[0] for r in conn.execute("SELECT student_uid FROM students WHERE student_uid IS NOT NULL AND student_uid != ''").fetchall())
    for _ in range(10000):
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        uid = f"{year_prefix}{letters}"
        if uid not in existing:
            return uid
    return None

def new_admission(data, username):
    """Create a new NA student — validates required fields including fees"""
    required = [("student_name","Student Name"),("father_name","Father Name"),
                ("mother_name","Mother Name"),("gross_tuition","Gross Tuition Fee"),
                ("misc_to_pay","MISC to Pay")]
    for field, label in required:
        v = data.get(field)
        if v is None or str(v).strip() == "" or (field in ("gross_tuition","misc_to_pay") and float(v or 0) == 0):
            return {"success":False,"error":f"{label} is required before admission number can be assigned."}

    conn = get_db()
    try:
        # Get next ref no
        conn.execute("UPDATE counters SET value=value+1 WHERE name='new_admission'")
        row = conn.execute("SELECT value FROM counters WHERE name='new_admission'").fetchone()
        ref_no = f"NA{row['value']:03d}"

        # Determine UID year prefix
        doa = data.get("date_of_admission","")
        year_prefix = "26" if "2026" in doa else "25"
        uid = _generate_uid(year_prefix, conn)

        gross   = float(data.get("gross_tuition",0) or 0)
        conc    = float(data.get("concession",0) or 0)
        net_t   = float(data.get("net_tuition",0) or 0) or (gross - conc)
        misc    = float(data.get("misc_to_pay",0) or 0)
        is_rte  = 1 if data.get("is_rte") else 0

        conn.execute("""INSERT INTO students
            (date_of_admission,sl_no,student_name,class,section,reference_no,
             father_name,mother_name,father_contact,mother_contact,status,
             gross_tuition,concession,net_tuition,misc_to_pay,comments,student_uid,is_rte)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("date_of_admission", str(datetime.now().day)+datetime.now().strftime("-%b-%Y")),
             data.get("sl_no",""), data["student_name"].strip(),
             data.get("grade",""), data.get("section",""), ref_no,
             data.get("father_name","").strip(), data.get("mother_name","").strip(),
             data.get("father_contact",""), data.get("mother_contact",""),
             "Admitted", gross, conc, net_t, misc,
             data.get("comments",""), uid or "", is_rte))
        conn.commit()
        from modules.auth import audit
        audit(username,"admin","NEW_ADMISSION",f"NA admitted: {data['student_name']} ref:{ref_no}")
        return {"success":True,"ref_no":ref_no,"student_uid":uid}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()

def re_admission(data, username):
    """Create a new RA student — validates required fields including fees"""
    required = [("student_name","Student Name"),("father_name","Father Name"),
                ("mother_name","Mother Name"),("gross_tuition","Gross Tuition Fee"),
                ("misc_to_pay","MISC to Pay")]
    for field, label in required:
        v = data.get(field)
        if v is None or str(v).strip() == "" or (field in ("gross_tuition","misc_to_pay") and float(v or 0) == 0):
            return {"success":False,"error":f"{label} is required before admission number can be assigned."}

    conn = get_db()
    try:
        conn.execute("UPDATE counters SET value=value+1 WHERE name='re_admission'")
        row = conn.execute("SELECT value FROM counters WHERE name='re_admission'").fetchone()
        ref_no = f"RA{row['value']:03d}"

        doa = data.get("date_of_admission","")
        year_prefix = "26" if "2026" in doa else "25"
        uid = _generate_uid(year_prefix, conn)

        gross   = float(data.get("gross_tuition",0) or 0)
        conc    = float(data.get("concession",0) or 0)
        net_t   = float(data.get("net_tuition",0) or 0) or (gross - conc)
        misc    = float(data.get("misc_to_pay",0) or 0)
        is_rte  = 1 if data.get("is_rte") else 0

        conn.execute("""INSERT INTO students
            (date_of_admission,sl_no,student_name,class,section,reference_no,
             father_name,mother_name,father_contact,mother_contact,status,
             gross_tuition,concession,net_tuition,misc_to_pay,comments,student_uid,is_rte)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("date_of_admission", str(datetime.now().day)+datetime.now().strftime("-%b-%Y")),
             data.get("sl_no",""), data["student_name"].strip(),
             data.get("grade",""), data.get("section",""), ref_no,
             data.get("father_name","").strip(), data.get("mother_name","").strip(),
             data.get("father_contact",""), data.get("mother_contact",""),
             "Admitted", gross, conc, net_t, misc,
             data.get("comments",""), uid or "", is_rte))
        conn.commit()
        from modules.auth import audit
        audit(username,"admin","RE_ADMISSION",f"RA admitted: {data['student_name']} ref:{ref_no}")
        return {"success":True,"ref_no":ref_no,"student_uid":uid}
    except Exception as e:
        conn.rollback()
        return {"success":False,"error":str(e)}
    finally:
        conn.close()
