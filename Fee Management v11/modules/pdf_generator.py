"""
PDF Generator — RPS Receipt v13
- Each receipt occupies exactly the top/bottom half of A4
- Three-line note section
- Larger note text and larger bold copy labels
"""
import os

_RECEIPTS_BASE = None

def set_receipts_path(path):
    global _RECEIPTS_BASE
    _RECEIPTS_BASE = path

def get_receipts_base():
    if _RECEIPTS_BASE:
        return _RECEIPTS_BASE
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.dirname(app_dir), "receipts")


def generate_receipt_pdf(data, fee_type):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (Table, TableStyle, Paragraph,
                                        Spacer, Image, Frame)
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.pdfgen import canvas as pdfcanvas

        # ── Output path ───────────────────────────────────────────────
        base_dir   = get_receipts_base()
        fee_folder = os.path.join(base_dir, fee_type)
        os.makedirs(fee_folder, exist_ok=True)
        safe_name    = data["student_name"].replace(" ", "_").replace("/", "-")
        pdf_filename = (f"{safe_name}_{data['receipt_no']}_"
                        f"{data['payment_date'].replace('-', '')}.pdf")
        pdf_path = os.path.join(fee_folder, pdf_filename)

        # ── Page geometry ─────────────────────────────────────────────
        PAGE_W, PAGE_H = A4          # 595.27 x 841.89 pt
        LM = RM = 12 * mm            # left/right margin
        VM = 5 * mm                  # tiny vertical margin top & bottom
        TW = PAGE_W - LM - RM        # usable width

        # Exact half-page for each receipt frame
        # Top frame:    y from (PAGE_H/2 + 2mm)  to  (PAGE_H - VM)
        # Bottom frame: y from VM                 to  (PAGE_H/2 - 2mm)
        MID  = PAGE_H / 2
        GAP  = 3 * mm                # gap each side of dashed line

        top_y = MID + GAP
        top_h = PAGE_H - VM - top_y  # height of top frame

        bot_y = VM
        bot_h = MID - GAP - bot_y    # height of bottom frame

        # ── Colours ───────────────────────────────────────────────────
        BLK  = colors.HexColor("#1a1a1a")
        WHT  = colors.white
        LGRY = colors.HexColor("#f2f2f2")
        MGRY = colors.HexColor("#cccccc")

        # ── Styles ────────────────────────────────────────────────────
        def sty(name, font="Helvetica", size=9, align=TA_LEFT,
                color=BLK, leading=None):
            return ParagraphStyle(name, fontName=font, fontSize=size,
                                  alignment=align, textColor=color,
                                  leading=leading or size + 3,
                                  spaceAfter=0, spaceBefore=0)

        hdr_s  = sty("hdr",  "Helvetica-Bold", 9,  TA_CENTER, WHT)
        lbl_s  = sty("lbl",  "Helvetica-Bold", 9,  TA_LEFT,   BLK)
        val_s  = sty("val",  "Helvetica",      9,  TA_LEFT,   BLK)
        amtr_s = sty("amtr", "Helvetica-Bold", 10, TA_RIGHT,  WHT)
        note1_s= sty("nt1",  "Helvetica-Bold", 9,  TA_LEFT,   BLK, leading=13)
        note2_s= sty("nt2",  "Helvetica",      9,  TA_LEFT,   BLK, leading=13)
        copy_s = sty("copy", "Helvetica-Bold", 11, TA_RIGHT,  BLK, leading=14)

        def H(t): return Paragraph(f"<b>{t}</b>", hdr_s)
        def L(t): return Paragraph(f"<b>{t}</b>", lbl_s)
        def V(t): return Paragraph(str(t) if t else "", val_s)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "img", "school_logo.png")

        # Column widths
        CW = [36*mm, 55*mm, 42*mm, TW - 133*mm]   # details 4-col
        PCW = [50*mm, 91*mm, TW - 141*mm]          # particulars 3-col
        NCW = [100*mm, TW - 100*mm]                 # note 2-col

        # ── Build one receipt's flowables ─────────────────────────────
        def build_receipt(copy_label):
            inner_rows = []

            # Logo
            if os.path.exists(logo_path):
                inner_rows.append([Image(logo_path, width=TW, height=36*mm)])
            else:
                inner_rows.append([Paragraph(
                    "<b>ROYAL PUBLIC SCHOOL</b>",
                    ParagraphStyle("bi", fontName="Helvetica-Bold",
                                   fontSize=16, alignment=TA_CENTER))])

            # Details table
            det_data = [
                [H("STUDENT DETAILS"), "", H("PAYMENT DETAILS"), ""],
                [L("STUDENT NAME"),    V(data["student_name"]),
                 L("RECEIPT NUMBER"),  Paragraph(f"<b>{data['receipt_no']}</b>", lbl_s)],
                [L("PARENT NAME"),     V(data["parent_name"]),
                 L("PAYMENT MODE"),    V(data["payment_mode"])],
                [L("GRADE"),           V(data["grade"]),
                 L("DATE OF PAYMENT"), V(data["payment_date"])],
                [L("SECTION"),         V(data.get("section") or ""),
                 L("REFERENCE NO."),   V(data["reference_no"])],
            ]
            det_tbl = Table(det_data, colWidths=CW)
            det_tbl.setStyle(TableStyle([
                ("SPAN",          (0,0),(1,0)),
                ("SPAN",          (2,0),(3,0)),
                ("INNERGRID",     (0,0),(-1,-1), 0.5, MGRY),
                ("BACKGROUND",    (0,0),(1,0),   BLK),
                ("BACKGROUND",    (2,0),(3,0),   BLK),
                ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHT, LGRY, WHT, LGRY]),
                ("LINEAFTER",     (1,0),(1,-1),  1.5, BLK),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("RIGHTPADDING",  (0,0),(-1,-1), 4),
            ]))
            inner_rows.append([det_tbl])

            # Particulars table
            par_data = [
                [H("PARTICULARS"),
                 H("AMOUNT"),
                 Paragraph(f"<b>Rs {data['amount']:,.0f}</b>", amtr_s)],
                [L(data["fee_type"]),
                 Paragraph(f"<b>{data['amount_words']}</b>", lbl_s), ""],
            ]
            par_tbl = Table(par_data, colWidths=PCW)
            par_tbl.setStyle(TableStyle([
                ("INNERGRID",     (0,0),(-1,-1), 0.5, MGRY),
                ("BACKGROUND",    (0,0),(-1,0),  BLK),
                ("BACKGROUND",    (0,1),(-1,1),  LGRY),
                ("SPAN",          (1,1),(2,1)),
                ("ALIGN",         (2,0),(2,0),   "RIGHT"),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("RIGHTPADDING",  (0,0),(-1,-1), 6),
            ]))
            inner_rows.append([par_tbl])

            # Note table — 3 rows
            note_data = [
                [Paragraph("<b>NOTE: This is a computer-generated receipt.</b>", note1_s),
                 Paragraph("<b>Collected By: _______________</b>", note1_s)],
                [Paragraph("Confirmation fee once paid will not be refunded "
                           "under any circumstances.", note2_s), ""],
                [Paragraph("Please consider carefully before enrolling your ward.",
                           note2_s), ""],
            ]
            note_tbl = Table(note_data, colWidths=NCW)
            note_tbl.setStyle(TableStyle([
                ("SPAN",          (0,1),(1,1)),
                ("SPAN",          (0,2),(1,2)),
                ("INNERGRID",     (0,0),(-1,-1), 0.5, MGRY),
                ("BACKGROUND",    (0,0),(-1,-1), LGRY),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 4),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("RIGHTPADDING",  (0,0),(-1,-1), 6),
            ]))
            inner_rows.append([note_tbl])

            # Outer border
            outer = Table(inner_rows, colWidths=[TW])
            outer.setStyle(TableStyle([
                ("BOX",           (0,0),(-1,-1), 1.8, BLK),
                ("TOPPADDING",    (0,0),(-1,-1), 0),
                ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ("LEFTPADDING",   (0,0),(-1,-1), 0),
                ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                ("LINEBELOW",     (0,0),(0,0),   1, BLK),
                ("LINEBELOW",     (0,1),(0,1),   1, BLK),
                ("LINEBELOW",     (0,2),(0,2),   1, BLK),
            ]))

            copy_para = Paragraph(f"<b>— {copy_label} —</b>", copy_s)
            return [outer, Spacer(1, 1.5*mm), copy_para]

        # ── Draw on canvas ────────────────────────────────────────────
        c = pdfcanvas.Canvas(pdf_path, pagesize=A4)

        # TOP HALF — Frame anchored to top of its zone, content flows down
        top_frame = Frame(LM, top_y, TW, top_h,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0,
                          showBoundary=0)
        top_story = build_receipt("SCHOOL COPY")
        top_frame.addFromList(top_story, c)

        # No separator line between the two receipts

        # BOTTOM HALF — Frame anchored to top of its zone (just below dashed line)
        bot_frame = Frame(LM, bot_y, TW, bot_h,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0,
                          showBoundary=0)
        bot_story = build_receipt("PARENT COPY")
        bot_frame.addFromList(bot_story, c)

        c.save()
        return {"pdf_path": pdf_path, "pdf_filename": pdf_filename}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"pdf_path": "", "pdf_filename": "", "error": str(e)}


def generate_cancellation_pdf(original_receipt, reason, cancelled_by):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER

        base_dir     = os.path.join(get_receipts_base(), "CANCELLED")
        os.makedirs(base_dir, exist_ok=True)
        pdf_filename = f"CANCELLED_{original_receipt['receipt_no']}.pdf"
        pdf_path     = os.path.join(base_dir, pdf_filename)

        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm,  bottomMargin=15*mm)
        story = []
        red    = ParagraphStyle("red",  fontName="Helvetica-Bold", fontSize=18,
                                textColor=colors.red, alignment=TA_CENTER)
        normal = ParagraphStyle("n",    fontName="Helvetica", fontSize=11, leading=16)

        story.append(Paragraph("RECEIPT CANCELLATION NOTICE", red))
        story.append(Spacer(1, 8*mm))
        rows = [
            ["Original Receipt No:",  original_receipt.get("receipt_no",   "")],
            ["Student Name:",         original_receipt.get("student_name",  "")],
            ["Amount:",               f"Rs {original_receipt.get('amount', 0):,.0f}"],
            ["Fee Type:",             original_receipt.get("fee_type",      "")],
            ["Payment Mode:",         original_receipt.get("payment_mode",  "")],
            ["Cancellation Reason:",  reason],
            ["Cancelled By:",         cancelled_by],
        ]
        t = Table(rows, colWidths=[60*mm, 110*mm])
        t.setStyle(TableStyle([
            ("BOX",           (0,0),(-1,-1), 1,   colors.black),
            ("INNERGRID",     (0,0),(-1,-1), 0.5, colors.grey),
            ("BACKGROUND",    (0,0),(0,-1),  colors.HexColor("#fdecea")),
            ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph(
            "<b>NOTE:</b> This receipt has been CANCELLED and the amount reversed. "
            "This document is the official cancellation record.", normal))
        doc.build(story)
        return {"pdf_path": pdf_path, "pdf_filename": pdf_filename}
    except Exception as e:
        return {"pdf_path": "", "pdf_filename": "", "error": str(e)}
