import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import get_settings
from app.models import Report

BRAND = colors.HexColor("#116B62")
TEXT = colors.HexColor("#18312F")
MUTED = colors.HexColor("#6C807C")
MINT = colors.HexColor("#DDF4ED")
AMBER = colors.HexColor("#FFF4DC")


def esc(value) -> str:
    """ReportLab paragraphs read <tags>; escape user- and AI-written text so it prints as plain text."""
    return escape(str(value if value is not None else ""))


def render_report_pdf(report: Report) -> bytes:
    a = report.analysis
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"DerMedics AI report #{report.id}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=BRAND, alignment=0, fontSize=20)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=TEXT, fontSize=13, spaceBefore=10)
    body = ParagraphStyle("body", parent=ss["BodyText"], textColor=TEXT, fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, textColor=MUTED, fontSize=8.5)

    story = [Paragraph("DerMedics AI — Skin analysis report", h1)]
    created = report.created_at.strftime("%d %b %Y, %H:%M") if report.created_at else ""
    story.append(Paragraph(f"Report #{report.id} • {created} • Region: {esc(a.region)}", small))
    story.append(Spacer(1, 8))

    subject = [
        ["Person", report.subject_name],
        ["Relationship", report.relationship_to_user],
        ["Age", str(report.subject_age) if report.subject_age is not None else "—"],
        ["Body area", a.body_area or "—"],
        ["Noticed", a.symptoms or "—"],
        ["Health notes", report.health_notes or "—"],
    ]
    t = Table([[Paragraph(k, small), Paragraph(esc(v), body)] for k, v in subject], colWidths=[35 * mm, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)

    img_path = get_settings().upload_dir / a.image_path
    if img_path.exists():
        try:
            story.append(Spacer(1, 6))
            story.append(RLImage(str(img_path), width=55 * mm, height=55 * mm, kind="proportional"))
        except Exception:
            pass

    story.append(Paragraph("AI analysis", h2))
    if a.status == "ai":
        result = f"<b>{esc(a.display_name)}</b> — model confidence {a.confidence * 100:.0f}%"
        if a.is_demo:
            result += " <font color='#B7791F'>(demo model — illustrative only)</font>"
        story.append(Paragraph(result, body))
        d = a.description or {}
        if d:
            story.append(Paragraph("About the condition", h2))
            story.append(Paragraph(esc(d.get("overview", "")), body))
            for title, key in (("Symptoms", "symptoms"), ("Precautions", "precautions")):
                if d.get(key):
                    story.append(Paragraph(f"<b>{title}</b>", body))
                    for item in d[key]:
                        story.append(Paragraph(f"• {esc(item)}", body))
            if d.get("when_to_see_doctor"):
                story.append(Paragraph(f"<b>When to see a doctor:</b> {esc(d['when_to_see_doctor'])}", body))
        if a.medicines:
            story.append(Paragraph("AI medicine suggestions (informational)", h2))
            rows = [["Option", "Type", "Notes"]]
            for m in a.medicines:
                rx = " (prescription required)" if m.get("prescription_required") else ""
                rows.append([Paragraph(esc(m["name"] + rx), body), m.get("type", ""),
                             Paragraph(esc(f"{m.get('usage_note', '')} {m.get('caution', '')}"), small)])
            mt = Table(rows, colWidths=[55 * mm, 22 * mm, None], repeatRows=1)
            mt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), MINT),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5E2DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(mt)
    else:
        story.append(Paragraph("<b>No reliable prediction.</b> The image may be unclear or the condition may not be "
                               "supported. No medicine suggestions are shown for uncertain results.", body))

    story.append(Spacer(1, 12))
    note = Table([[Paragraph("<b>Safety first.</b> This report provides informational skin-health support, not a "
                             "diagnosis or prescription. Confirm suitability, side effects and local availability with "
                             "a pharmacist or dermatologist. Seek urgent care for severe or rapidly spreading symptoms.",
                             body)]])
    note.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER), ("BOX", (0, 0), (-1, -1), 0, AMBER),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(note)
    story.append(Spacer(1, 6))
    story.append(Paragraph(esc(f"Model: {a.model_version} • Text source: {a.llm_source}"), small))

    doc.build(story)
    return buf.getvalue()
