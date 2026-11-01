"""Patient report PDF: logo header, patient card + photo, disease details with a confidence ring, medicine tiles and
dermatologist recommendations, in the app's purple / lavender palette."""

import io
from datetime import UTC
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import get_settings
from app.models import Report
from app.schemas import DermatologistOut

# Palette (matches the app's light theme)
BRAND = colors.HexColor("#6D3FD1")
DEEP = colors.HexColor("#3A1F78")
LILAC = colors.HexColor("#B69CFF")
LAVENDER = colors.HexColor("#EFE8FD")
WASH = colors.HexColor("#F6F2FE")  # page header background
TEXT = colors.HexColor("#1E1633")
MUTED = colors.HexColor("#6F6787")
BORDER = colors.HexColor("#E3DCF2")
TRACK = colors.HexColor("#ECE7F6")
AMBER = colors.HexColor("#FFF6E0")
AMBER_TEXT = colors.HexColor("#7A5200")
RING = ["#3A1F78", "#5228B0", "#6D3FD1", "#8A5CF0", "#A67CFF", "#C9A8FF"]
# Pastel tiles for medicine suggestions: (background, icon colour)
TILES = [
    ("#E4EEFF", "#3B5BDB"),
    ("#E3F6EC", "#2F9E6B"),
    ("#FFF4D1", "#C08A00"),
    ("#EFE8FD", "#6D3FD1"),
    ("#FDE7F1", "#C2417A"),
]

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
LOGO = get_settings().data_dir / "logo.png"


def esc(value) -> str:
    """ReportLab paragraphs read <tags>; escape user- and AI-written text so it prints as plain text."""
    return escape(str(value if value is not None else ""))


def _style(name, size=9.5, color=TEXT, bold=False, align=0, leading=None, space_after=0) -> ParagraphStyle:
    return ParagraphStyle(name, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, textColor=color,
                          alignment=align, leading=leading or size * 1.38, spaceAfter=space_after)


TITLE = _style("title", 21, DEEP, bold=True, align=TA_CENTER, leading=26)
CARD_TITLE = _style("card_title", 12.5, TEXT, bold=True, space_after=6)
SECTION = _style("section", 11, DEEP, bold=True, align=TA_CENTER)
SUB = _style("sub", 9.5, BRAND, bold=True, space_after=2)
BODY = _style("body", 9.5)
SMALL = _style("small", 8, MUTED)
LABEL = _style("label", 9.5, MUTED)
VALUE = _style("value", 9.5, TEXT, bold=True)
CAPTION = _style("caption", 8.5, TEXT, bold=True, align=TA_CENTER)
DATE = _style("date", 8.5, MUTED, align=TA_RIGHT, leading=12)
TILE_NAME = _style("tile_name", 9, TEXT, bold=True, align=TA_CENTER, leading=11.5)
TILE_NOTE = _style("tile_note", 7.5, MUTED, align=TA_CENTER, leading=9.5)


def _card(content, width, border=BORDER, border_width=0.8, background=colors.white, padding=10) -> Table:
    """A rounded white panel around one flowable (or a list of them)."""
    t = Table([[content]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), border_width, border),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _bullets(items: list[str], style=BODY) -> list[Paragraph]:
    return [Paragraph(f"<font color='#6D3FD1'>•</font>&nbsp; {esc(i)}", style) for i in items if str(i).strip()]


def _confidence_ring(confidence: float | None, size: float = 40 * mm) -> Drawing:
    """Donut chart: the coloured arc is the model's confidence, starting at 12 o'clock and going clockwise."""
    d = Drawing(size, size)
    c = size / 2
    outer, inner = size / 2 - 1, size / 2 - 1 - 8.5
    d.add(Wedge(c, c, outer, 0, 360, radius1=inner, fillColor=TRACK, strokeColor=None))
    if confidence:
        sweep = 360 * max(0.0, min(1.0, confidence))
        step = sweep / len(RING)
        for i, colour in enumerate(RING):
            end = 90 - i * step
            d.add(Wedge(c, c, outer, end - step - 0.3, end, radius1=inner,
                        fillColor=colors.HexColor(colour), strokeColor=None))
    d.add(Circle(c, c, inner - 0.5, fillColor=colors.white, strokeColor=None))
    label = f"{confidence * 100:.0f}%" if confidence else "—"
    d.add(String(c, c + 1, label, fontName="Helvetica-Bold", fontSize=19, fillColor=DEEP, textAnchor="middle"))
    d.add(String(c, c - 10, "AI confidence", fontName="Helvetica", fontSize=7, fillColor=MUTED, textAnchor="middle"))
    return d


def _capsule(icon_colour: str) -> Drawing:
    """Small capsule-and-tablet icon for a medicine tile."""
    col = colors.HexColor(icon_colour)
    d = Drawing(36, 18)
    # Capsule: coloured left half, outlined right half, plus a round tablet.
    d.add(Rect(1, 4, 24, 11, rx=5.5, ry=5.5, fillColor=colors.white, strokeColor=col, strokeWidth=1.3))
    d.add(Rect(1, 4, 13, 11, rx=5.5, ry=5.5, fillColor=col, strokeColor=col, strokeWidth=1.3))
    d.add(Rect(8, 4, 5.5, 11, fillColor=col, strokeColor=None))
    d.add(Circle(30.5, 7, 4.5, fillColor=colors.white, strokeColor=col, strokeWidth=1.3))
    return d


def _header(report: Report) -> list:
    created = report.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    date = created.strftime("%d/%m/%Y") if created else ""
    time = created.strftime("%I:%M %p") if created else ""
    logo = RLImage(str(LOGO), width=20 * mm, height=20 * mm) if LOGO.exists() else Spacer(1, 20 * mm)
    top = Table([["", logo, Paragraph(f"Date: {date}<br/>{time}", DATE)]],
                colWidths=[CONTENT_W / 3] * 3)
    top.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    title = Paragraph("<font color='#6D3FD1'>DerMedics AI</font> - Patient report", TITLE)
    return [top, Spacer(1, 3), title, Spacer(1, 10)]


def _patient_and_photo(report: Report) -> Table:
    a = report.analysis
    rows = [
        ("Name", report.subject_name),
        ("Report ID", f"DM-{report.id:06d}"),
        ("Age", report.subject_age if report.subject_age is not None else "—"),
        ("Relationship", report.relationship_to_user),
        ("Body area", a.body_area or "—"),
        ("Region", a.region or "—"),
    ]
    info = Table([[Paragraph(k, LABEL), Paragraph(esc(v), VALUE)] for k, v in rows], colWidths=[26 * mm, None])
    info.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                              ("TOPPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    left_w, gap = 100 * mm, 6 * mm
    right_w = CONTENT_W - left_w - gap
    left = _card([Paragraph("Patient Personal Info", CARD_TITLE), info], left_w)

    img_path = get_settings().upload_dir / a.image_path
    photo_w, photo_h = right_w - 8, 44 * mm
    try:
        photo = RLImage(str(img_path), width=photo_w, height=photo_h, kind="proportional")
    except Exception:
        photo = Paragraph("Photo unavailable", SMALL)
    framed = _card(photo, right_w, border=BRAND, border_width=1.4, padding=4)
    right = [framed, Spacer(1, 4), Paragraph("Patient uploaded skin image", CAPTION)]

    row = Table([[left, "", right]], colWidths=[left_w, gap, right_w])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return row


def _disease_details(report: Report) -> Table:
    a = report.analysis
    d = a.description or {}
    inner_w = CONTENT_W - 20
    ring_w = 44 * mm
    if a.status == "ai":
        head = [Paragraph(esc(a.display_name or d.get("name", "")), _style("cond", 13, BRAND, bold=True, space_after=4))]
        overview = d.get("overview") or "No description is available for this condition."
        head.append(Paragraph(esc(overview), BODY))
        if a.is_demo:
            head.append(Paragraph("Demo model: results are illustrative only.", SMALL))
        confidence = a.confidence
    else:
        head = [Paragraph("Inconclusive result", _style("cond", 13, BRAND, bold=True, space_after=4)),
                Paragraph("The AI could not give a reliable result for this photo. The image may be unclear, or the "
                          "condition may not be one the model supports. Please consult a dermatologist.", BODY)]
        confidence = None
    top = Table([[_confidence_ring(confidence), head]], colWidths=[ring_w, inner_w - ring_w])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    parts = [Paragraph("Disease Details", CARD_TITLE), top]

    # Two-column detail grid; empty sections are left out.
    sections = [(title, d.get(key) or []) for title, key in (
        ("Symptoms", "symptoms"), ("Causes &amp; triggers", "causes"),
        ("Risk factors", "risk_factors"), ("Self-care &amp; precautions", "precautions"))]
    sections = [(t, items) for t, items in sections if items] if a.status == "ai" else []
    if sections:
        col_w = (inner_w - 8) / 2
        cells = [[Paragraph(t, SUB), *_bullets(items)] for t, items in sections]
        if len(cells) % 2:
            cells.append([""])
        grid = Table([[cells[i], cells[i + 1]] for i in range(0, len(cells), 2)], colWidths=[col_w + 8, col_w])
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
        parts += [Spacer(1, 4), _rule(inner_w), grid]
    if a.status == "ai" and d.get("outlook"):
        parts += [Spacer(1, 4), Paragraph("Outlook", SUB), Paragraph(esc(d["outlook"]), BODY)]
    return _card(parts, CONTENT_W)


def _rule(width: float) -> Table:
    t = Table([[""]], colWidths=[width], rowHeights=[1])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.6, BORDER)]))
    return t


def _medicines(report: Report) -> list:
    a = report.analysis
    meds = a.medicines or []
    if a.status != "ai" or not meds:
        return []
    meds = meds[:5]
    gap = 5
    tile_w = (CONTENT_W - gap * (len(meds) - 1)) / len(meds)
    tiles = []
    for i, m in enumerate(meds):
        bg, icon = TILES[i % len(TILES)]
        kind = esc(m.get("type", "")) + (" · Prescription" if m.get("prescription_required") else " · OTC")
        content = [_capsule(icon), Spacer(1, 3), Paragraph(esc(m.get("name", "")), TILE_NAME),
                   Paragraph(kind.strip(" ·"), TILE_NOTE)]
        if m.get("usage_note"):
            content += [Spacer(1, 2), Paragraph(esc(m["usage_note"]), TILE_NOTE)]
        tiles.append((content, bg))
    # Same height for every tile: measure the tallest, then build them all at that height.
    height = max(_card(c, tile_w, padding=6).wrap(tile_w, PAGE_H)[1] for c, _ in tiles)
    tiles = [_tile(c, tile_w, height, bg) for c, bg in tiles]
    row_cells, widths = [], []
    for i, t in enumerate(tiles):
        if i:
            row_cells.append("")
            widths.append(gap)
        row_cells.append(t)
        widths.append(tile_w)
    row = Table([row_cells], colWidths=widths)
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    cautions = [f"{m.get('name')}: {m.get('caution')}" for m in meds if m.get("caution")]
    out = [Paragraph("MEDICINE SUGGESTIONS", SECTION), Spacer(1, 6), row, Spacer(1, 5)]
    if cautions:
        out.append(Paragraph("<b>Cautions.</b> " + esc(" • ".join(cautions)), SMALL))
    out.append(Paragraph("Informational only: confirm suitability, dose and availability with a pharmacist or doctor. "
                         "Prescription items need a doctor's assessment.", SMALL))
    return [KeepTogether(out), Spacer(1, 8), _rule(CONTENT_W), Spacer(1, 8)]


def _tile(content, width: float, height: float, bg: str) -> Table:
    t = Table([[content]], colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        *[(side, (0, 0), (-1, -1), 6) for side in ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")],
    ]))
    return t


def _recommendations(report: Report, doctors: list[DermatologistOut]) -> Table:
    a = report.analysis
    d = a.description or {}
    items = []
    if d.get("when_to_see_doctor"):
        items.append(d["when_to_see_doctor"])
    items += d.get("dermatologist_care") or []
    if a.status != "ai":
        items = ["Book an in-person skin examination with a dermatologist.",
                 "Take a clear, well-lit photo to show the doctor how the area has changed.",
                 "Seek urgent care for rapid spreading, bleeding, fever or severe pain."]
    parts = [Paragraph("Specialist Dermatologist Recommendations", CARD_TITLE), *_bullets(items)]
    if doctors:
        parts += [Spacer(1, 6), Paragraph("Dermatologists you can contact", SUB)]
        for doc in doctors[:3]:
            where = ", ".join(x for x in (doc.clinic, doc.city) if x)
            line = f"<b>{esc(doc.name)}</b>" + (f" — {esc(where)}" if where else "")
            if doc.phone:
                line += f" • {esc(doc.phone)}"
            parts.append(Paragraph(f"<font color='#6D3FD1'>•</font>&nbsp; {line}", BODY))
    return _card(parts, CONTENT_W, border=BRAND, border_width=1.2)


def _draw_page(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        # Soft lavender wash behind the header and top cards.
        canvas.setFillColor(WASH)
        canvas.rect(0, PAGE_H - 118 * mm, PAGE_W, 118 * mm, stroke=0, fill=1)
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 3, PAGE_W, 3, stroke=0, fill=1)
    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 8 * mm, "DerMedics AI • Informational skin-health support, not a medical diagnosis.")
    canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_report_pdf(report: Report, doctors: list[DermatologistOut] | None = None) -> bytes:
    a = report.analysis
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=12 * mm,
                            bottomMargin=18 * mm, title=f"DerMedics AI patient report DM-{report.id:06d}",
                            author="DerMedics AI")
    story = _header(report)
    story += [_patient_and_photo(report), Spacer(1, 10), _disease_details(report), Spacer(1, 12)]
    story += _medicines(report)
    story += [_recommendations(report, doctors or []), Spacer(1, 10)]

    notes = []
    if a.symptoms:
        notes.append(f"<b>What was noticed:</b> {esc(a.symptoms)}")
    if report.health_notes:
        notes.append(f"<b>Health notes:</b> {esc(report.health_notes)}")
    notes.append("<b>Safety first.</b> This report provides informational skin-health support, not a diagnosis or "
                 "prescription. Seek urgent care for severe, painful or rapidly spreading symptoms.")
    story.append(_card([Paragraph(n, _style("note", 8.5, AMBER_TEXT)) for n in notes], CONTENT_W,
                       border=AMBER, background=AMBER, padding=8))
    story += [Spacer(1, 4), Paragraph(esc(f"Model: {a.model_version} • Text source: {a.llm_source}"), SMALL)]

    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return buf.getvalue()
