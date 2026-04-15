"""Daily Report module v4 - with report log, fee change tracking, RTE bifurcation"""
from database.db import get_db
from datetime import datetime, date, timedelta
import re, json

def get_daily_report_data(report_date=None):
    if not report_date:
        report_date = date.today().strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(report_date, "%Y-%m-%d").date()
    except:
        return {"success": False, "error": "Invalid date format"}

    yesterday    = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    date_display = str(dt.day) + dt.strftime("-%b-%Y")

    conn = get_db()
    try:
        # ── Admission counts ───────────────────────────────────────────────
        total_ra  = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no LIKE 'RA%'").fetchone()[0]
        total_na  = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no LIKE 'NA%'").fetchone()[0]
        total_rte = conn.execute("SELECT COUNT(*) FROM students WHERE is_rte=1").fetchone()[0]
        total_rte_ra = conn.execute("SELECT COUNT(*) FROM students WHERE is_rte=1 AND reference_no LIKE 'RA%'").fetchone()[0]
        total_rte_na = conn.execute("SELECT COUNT(*) FROM students WHERE is_rte=1 AND reference_no LIKE 'NA%'").fetchone()[0]
        total_admitted = total_ra + total_na
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        waiting   = total_students - total_admitted

        new_ra_today = conn.execute(
            "SELECT COUNT(*) FROM students WHERE reference_no LIKE 'RA%' AND date_of_admission=?",
            (date_display,)).fetchone()[0]
        new_na_today = conn.execute(
            "SELECT COUNT(*) FROM students WHERE reference_no LIKE 'NA%' AND date_of_admission=?",
            (date_display,)).fetchone()[0]
        new_admissions_today = new_ra_today + new_na_today

        new_admissions_list = [dict(r) for r in conn.execute("""
            SELECT student_name, reference_no, class, section, date_of_admission,
                   net_tuition, misc_to_pay, gross_tuition, concession, is_rte, student_uid
            FROM students
            WHERE date_of_admission=? AND (reference_no LIKE 'NA%' OR reference_no LIKE 'RA%')
            ORDER BY reference_no""", (date_display,)).fetchall()]

        # ── Validate: every admitted student needs net_tuition AND misc ──
        try:
            incomplete_rows = [dict(r) for r in conn.execute("""
                SELECT s.reference_no, s.student_name, s.class,
                       s.gross_tuition, s.concession, s.net_tuition, s.misc_to_pay,
                       COALESCE((SELECT SUM(m.amount) FROM misc_transactions m
                                  WHERE m.reference_no=s.reference_no AND m.status='active'),0) AS misc_paid
                FROM students s
                WHERE s.reference_no IS NOT NULL AND s.reference_no != ''
                AND (
                    s.net_tuition IS NULL OR s.net_tuition = 0
                    OR ((s.misc_to_pay IS NULL OR s.misc_to_pay = 0)
                        AND COALESCE((SELECT SUM(m.amount) FROM misc_transactions m
                                       WHERE m.reference_no=s.reference_no AND m.status='active'),0) = 0)
                )
                ORDER BY s.reference_no""").fetchall()]
        except Exception:
            incomplete_rows = []

        if incomplete_rows:
            return {
                "success": False,
                "error": f"{len(incomplete_rows)} student(s) missing Net Tuition and/or MISC to Pay. Fill in Total Balance tab first.",
                "incomplete_rows": incomplete_rows,
            }

        # ── Fee structure totals ───────────────────────────────────────────
        totals = conn.execute("""
            SELECT
                COALESCE(SUM(gross_tuition), 0)  AS gross_total,
                COALESCE(SUM(concession), 0)     AS concession_total,
                COALESCE(SUM(net_tuition), 0)    AS net_tuition_total,
                COALESCE(SUM(misc_to_pay), 0)    AS misc_total,
                COALESCE(SUM(net_tuition + COALESCE(misc_to_pay,0)), 0) AS total_payable
            FROM students WHERE reference_no IS NOT NULL AND reference_no != ''
        """).fetchone()

        gross_total               = float(totals["gross_total"])
        concession_total          = float(totals["concession_total"])
        net_tuition_total         = float(totals["net_tuition_total"])
        misc_total_fees           = float(totals["misc_total"])
        total_payable             = float(totals["total_payable"])
        net_payable_academic_year = total_payable

        # ── Collections ───────────────────────────────────────────────────
        collected_so_far = float(conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND DATE(created_at)<=?",
            (report_date,)).fetchone()[0])

        tuition_neft = float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND fee_type='TUITION' AND payment_mode='NEFT' AND DATE(created_at)=?", (report_date,)).fetchone()[0])
        tuition_cash = float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND fee_type='TUITION' AND payment_mode='CASH' AND DATE(created_at)=?", (report_date,)).fetchone()[0])
        misc_neft    = float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND fee_type='MISC'    AND payment_mode='NEFT' AND DATE(created_at)=?", (report_date,)).fetchone()[0])
        misc_cash    = float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND fee_type='MISC'    AND payment_mode='CASH' AND DATE(created_at)=?", (report_date,)).fetchone()[0])

        collected_neft    = tuition_neft + misc_neft
        collected_cash    = tuition_cash + misc_cash
        tuition_collected = tuition_neft + tuition_cash
        misc_collected    = misc_neft    + misc_cash
        total_today       = collected_neft + collected_cash

        collected_before_today = float(conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE status='active' AND DATE(created_at)<?",
            (report_date,)).fetchone()[0])

        # ── Outstanding ───────────────────────────────────────────────────
        outstanding_as_of_today_A = net_payable_academic_year - collected_so_far
        outstanding_yesterday     = net_payable_academic_year - collected_before_today
        outstanding_today_B       = outstanding_yesterday - total_today
        outstanding_as_of_today   = outstanding_today_B

        # ── Today's receipts ──────────────────────────────────────────────
        receipts_today = [dict(r) for r in conn.execute("""
            SELECT receipt_no, student_name, reference_no, grade, fee_type,
                   payment_mode, amount, payment_date
            FROM receipt_log WHERE status='active' AND DATE(created_at)=?
            ORDER BY created_at""", (report_date,)).fetchall()]

        # ── Fee change log since last report ──────────────────────────────
        # Find the most recent previous report generation time
        last_report = conn.execute("""
            SELECT generated_at FROM daily_report_log
            ORDER BY generated_at DESC LIMIT 1""").fetchone()
        last_report_time = last_report["generated_at"] if last_report else "2000-01-01 00:00:00"

        # Fee changes since the last report was generated (any unreported changes)
        fee_changes = [dict(r) for r in conn.execute("""
            SELECT reference_no, student_name, field_changed, old_value, new_value,
                   changed_by, changed_at
            FROM fee_change_log
            WHERE reported = 0
            ORDER BY changed_at""").fetchall()]

        # ── Mismatch detection ────────────────────────────────────────────
        mismatch = abs(outstanding_as_of_today_A - outstanding_today_B) > 0.01
        mismatch_reasons = []

        if mismatch:
            # Include fee changes as mismatch reasons
            for fc in fee_changes:
                mismatch_reasons.append({
                    "type":    "fee_edit",
                    "student": f"{fc['student_name']} ({fc['reference_no']})",
                    "field":   fc["field_changed"].replace("_"," ").title(),
                    "old_val": f"₹{float(fc['old_value'] or 0):,.0f}",
                    "new_val": f"₹{float(fc['new_value'] or 0):,.0f}",
                    "time":    fc["changed_at"],
                    "by":      fc["changed_by"],
                })

            # Check audit log for fee edits today
            fee_audit = conn.execute("""
                SELECT username, action, details, timestamp FROM audit_log
                WHERE DATE(timestamp)=?
                AND (action LIKE '%TUITION%' OR action LIKE '%EDIT_STUDENT%')
                ORDER BY timestamp""", (report_date,)).fetchall()

            for a in fee_audit:
                details = a["details"] or ""
                if any(f in details for f in ["concession","net_tuition","gross_tuition","misc_to_pay"]):
                    id_match = re.search(r'id:(\d+)', details)
                    sname = "Unknown"
                    if id_match:
                        sr = conn.execute("SELECT student_name, reference_no FROM students WHERE id=?",
                                          (int(id_match.group(1)),)).fetchone()
                        if sr:
                            sname = f"{sr['student_name']} ({sr['reference_no']})"
                    field = "fee value"
                    if "concession"     in details: field = "Concession"
                    elif "gross_tuition" in details: field = "Gross Tuition"
                    elif "net_tuition"   in details: field = "Net Tuition"
                    elif "misc_to_pay"   in details: field = "MISC to Pay"
                    chg = re.search(r"'([^']*)'->\'([^']*)'", details)
                    # Avoid duplicates from fee_change_log
                    already = any(r.get("student","").startswith(sname.split(" (")[0]) and
                                  r.get("field","") == field for r in mismatch_reasons)
                    if not already:
                        mismatch_reasons.append({
                            "type":    "fee_edit",
                            "student": sname,
                            "field":   field,
                            "old_val": chg.group(1) if chg else "—",
                            "new_val": chg.group(2) if chg else "—",
                            "time":    a["timestamp"],
                            "by":      a["username"],
                        })

            # Receipts cancelled today
            for cr in conn.execute("""
                SELECT original_receipt_no, student_name, amount, fee_type,
                       reason, cancelled_by, cancelled_at
                FROM cancelled_receipts WHERE DATE(cancelled_at)=?
                ORDER BY cancelled_at""", (report_date,)).fetchall():
                mismatch_reasons.append({
                    "type":    "cancellation",
                    "student": cr["student_name"],
                    "field":   f"{cr['fee_type']} Receipt Cancelled",
                    "old_val": f"Receipt {cr['original_receipt_no']} counted",
                    "new_val": f"₹{cr['amount']:,.0f} reversed",
                    "time":    cr["cancelled_at"],
                    "by":      cr["cancelled_by"] or "—",
                })

            if not mismatch_reasons:
                mismatch_reasons.append({
                    "type":    "unknown",
                    "student": "—",
                    "field":   "Fee structure modified (change predates audit log)",
                    "old_val": f"₹{outstanding_today_B:,.2f}",
                    "new_val": f"₹{outstanding_as_of_today_A:,.2f}",
                    "time":    "—",
                    "by":      "—",
                })

        return {
            "success":                   True,
            "report_date":               report_date,
            "mismatch":                  mismatch,
            "mismatch_diff":             round(outstanding_as_of_today_A - outstanding_today_B, 2),
            "mismatch_reasons":          mismatch_reasons,
            "fee_changes":               fee_changes,
            # Admissions
            "total_students":            total_students,
            "total_admitted":            total_admitted,
            "waiting":                   waiting,
            "total_ra":                  total_ra,
            "total_na":                  total_na,
            "total_rte":                 total_rte,
            "total_rte_ra":              total_rte_ra,
            "total_rte_na":              total_rte_na,
            "new_ra_today":              new_ra_today,
            "new_na_today":              new_na_today,
            "new_admissions_today":      new_admissions_today,
            "new_admissions_list":       new_admissions_list,
            # Fee structure
            "gross_total":               gross_total,
            "concession_total":          concession_total,
            "net_tuition_total":         net_tuition_total,
            "misc_total_fees":           misc_total_fees,
            "total_payable":             total_payable,
            "net_payable_academic_year": net_payable_academic_year,
            # Collections
            "collected_so_far":          collected_so_far,
            "collected_before_today":    collected_before_today,
            "tuition_neft":              tuition_neft,
            "tuition_cash":              tuition_cash,
            "misc_neft":                 misc_neft,
            "misc_cash":                 misc_cash,
            "collected_neft":            collected_neft,
            "collected_cash":            collected_cash,
            "tuition_collected":         tuition_collected,
            "misc_collected":            misc_collected,
            "total_today":               total_today,
            # Outstanding
            "outstanding_yesterday":     outstanding_yesterday,
            "outstanding_as_of_today":   outstanding_as_of_today,
            "receipts_today":            receipts_today,
            # Last report time
            "last_report_time":          last_report_time,
        }
    finally:
        conn.close()


def log_daily_report(report_date, generated_by, report_data):
    """Save report to log and mark fee_changes as reported"""
    conn = get_db()
    try:
        conn.execute("""INSERT INTO daily_report_log
            (report_date, generated_by, report_json)
            VALUES (?,?,?)""",
            (report_date, generated_by, json.dumps({
                "total_today": report_data.get("total_today",0),
                "outstanding": report_data.get("outstanding_as_of_today",0),
                "admissions":  report_data.get("total_admitted",0),
            })))
        # Mark all unreported fee changes as reported
        conn.execute("UPDATE fee_change_log SET reported=1 WHERE reported=0")
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_report_log():
    """Get list of all generated daily reports"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, report_date, generated_by, generated_at, report_json
            FROM daily_report_log ORDER BY generated_at DESC""").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_old_reports(days=60):
    """Delete reports older than N days"""
    conn = get_db()
    try:
        cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        conn.execute("DELETE FROM daily_report_log WHERE DATE(generated_at) < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()
