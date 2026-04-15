"""Dashboard module v3"""
from database.db import get_db

def get_dashboard_stats():
    conn = get_db()
    try:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        admitted       = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no IS NOT NULL AND reference_no!=''").fetchone()[0]
        ra_count       = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no LIKE 'RA%'").fetchone()[0]
        na_count       = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no LIKE 'NA%'").fetchone()[0]
        no_ref         = conn.execute("SELECT COUNT(*) FROM students WHERE reference_no IS NULL OR reference_no=''").fetchone()[0]
        receipts_today = conn.execute("SELECT COUNT(*) FROM receipt_log WHERE DATE(created_at)=DATE('now','localtime') AND status='active'").fetchone()[0]
        collected_today= conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE DATE(created_at)=DATE('now','localtime') AND status='active'").fetchone()[0]
        tuition_total  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE fee_type='TUITION' AND status='active'").fetchone()[0]
        misc_total     = conn.execute("SELECT COALESCE(SUM(amount),0) FROM receipt_log WHERE fee_type='MISC' AND status='active'").fetchone()[0]

        # Total outstanding = sum of (net_tuition + misc_to_pay - neft_paid - cash_paid) for all admitted students
        outstanding_row = conn.execute("""
            SELECT COALESCE(SUM(
                COALESCE(net_tuition,0) + COALESCE(misc_to_pay,0)
                - COALESCE(neft_paid,0) - COALESCE(cash_paid,0)
            ), 0)
            FROM students
            WHERE reference_no IS NOT NULL AND reference_no != ''
            AND (net_tuition > 0 OR misc_to_pay > 0)
        """).fetchone()[0]
        total_outstanding = max(0, float(outstanding_row))

        counters = {r["name"]:r["value"] for r in conn.execute("SELECT name,value FROM counters").fetchall()}
        # Use actual DB counts (not counters, which can drift if receipts are deleted)
        tuition_receipt_count = conn.execute("SELECT COUNT(*) FROM receipt_log WHERE fee_type='TUITION' AND status='active'").fetchone()[0]
        misc_receipt_count    = conn.execute("SELECT COUNT(*) FROM receipt_log WHERE fee_type='MISC'    AND status='active'").fetchone()[0]
        recent   = conn.execute("""SELECT receipt_no,student_name,amount,fee_type,payment_mode,
                                          payment_date,created_by,created_at,pdf_path
                                   FROM receipt_log WHERE status='active'
                                   ORDER BY created_at DESC LIMIT 10""").fetchall()
        payment_breakdown = conn.execute("""SELECT payment_mode,COUNT(*) as count,SUM(amount) as total
                                            FROM receipt_log WHERE status='active' GROUP BY payment_mode""").fetchall()
        return {
            "total_students":   total_students,
            "admitted":         admitted,
            "ra_count":         ra_count,
            "na_count":         na_count,
            "no_ref":           no_ref,
            "receipts_today":   receipts_today,
            "collected_today":  collected_today,
            "tuition_total":    tuition_total,
            "misc_total":       misc_total,
            "total_outstanding": total_outstanding,
            "counters":         counters,
            "tuition_receipt_count": tuition_receipt_count,
            "misc_receipt_count":    misc_receipt_count,
            "recent_receipts":  [dict(r) for r in recent],
            "payment_breakdown":[dict(r) for r in payment_breakdown],
        }
    finally:
        conn.close()
