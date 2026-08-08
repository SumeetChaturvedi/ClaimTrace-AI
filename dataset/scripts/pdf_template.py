"""Rendering engine implementing the Dataset V2 PDF Template Specification
(Dataset V2 - Phase 2A - Task 01).

This module contains NO document content. It only lays out whatever
structured data it is given (metadata fields + body blocks, all supplied
verbatim by the caller) inside the letterhead / header / footer / metadata
box / signature block chrome defined by the template spec. It performs no
wording changes, no summarization, and no paraphrasing of any kind -
strings passed in are rendered character-for-character (subject to XML
escaping required by the rendering library, and reflowing of line breaks
that were purely presentational in the source markdown).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.pdfgen import canvas as canvas_module
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Font registration.
#
# The base14 Times-Roman font (WinAnsi/Latin-1 only) cannot render every
# character present in the approved source text -- notably the "->" arrow
# (U+2192) used in a document-chain summary in Scenario 6 (DRPN-NRB4-001).
# This is a genuine rendering limitation, not a design choice: without it,
# an approved character in an approved document would silently fail to
# render. Fixed once, at the font level, by embedding a full-coverage TTF
# (macOS system Times New Roman) instead of substituting or dropping the
# character. No document wording is changed by this fix.
# ---------------------------------------------------------------------------
_FONT_DIR = "/System/Library/Fonts/Supplemental"
try:
    pdfmetrics.registerFont(TTFont("TimesNR", f"{_FONT_DIR}/Times New Roman.ttf"))
    pdfmetrics.registerFont(TTFont("TimesNR-Bold", f"{_FONT_DIR}/Times New Roman Bold.ttf"))
    pdfmetrics.registerFont(TTFont("TimesNR-Italic", f"{_FONT_DIR}/Times New Roman Italic.ttf"))
    pdfmetrics.registerFont(TTFont("TimesNR-BoldItalic", f"{_FONT_DIR}/Times New Roman Bold Italic.ttf"))
    _BODY_FONT = "TimesNR"
    _BODY_FONT_BOLD = "TimesNR-Bold"
    _BODY_FONT_ITALIC = "TimesNR-Italic"
except Exception:  # pragma: no cover - fallback if the TTF isn't present
    _BODY_FONT = "Times-Roman"
    _BODY_FONT_BOLD = "Times-Bold"
    _BODY_FONT_ITALIC = "Times-Italic"

# ---------------------------------------------------------------------------
# Part A.16 - Margins
# ---------------------------------------------------------------------------
PAGE_SIZE = A4
MARGIN_TOP = 25 * mm
MARGIN_BOTTOM = 20 * mm
MARGIN_LEFT = 22 * mm
MARGIN_RIGHT = 22 * mm

# Reserve space at the top of every page for the letterhead header band and
# at the bottom for the footer, so the content Frame never collides with them.
HEADER_BAND_HEIGHT = 30 * mm
FOOTER_BAND_HEIGHT = 12 * mm

# ---------------------------------------------------------------------------
# Part A.1 / A.3 - Letterhead identities
# ---------------------------------------------------------------------------
LETTERHEADS = {
    "EMPLOYER": dict(
        wordmark="NHIA",
        subtext="National Highways Infrastructure Authority",
        legal_name="National Highways Infrastructure Authority",
        address=["NHIA Project Office, Plot 14, Sector 9, Government Complex, Vantara City"],
        rule_color=colors.HexColor("#7A1F2B"),
    ),
    "ENGINEER": dict(
        wordmark="MERIDIAN",
        subtext="Engineering Consultants",
        legal_name="Meridian Engineering Consultants",
        address=["Meridian House, 22 Riverside Avenue, Vantara City"],
        rule_color=colors.HexColor("#1F3F5C"),
    ),
    "CONTRACTOR": dict(
        wordmark="SAGARA",
        subtext="Constructions Pvt. Ltd.",
        legal_name="Sagara Constructions Pvt. Ltd.",
        address=["Sagara House, 8 Industrial Estate Road, Vantara City"],
        rule_color=colors.HexColor("#2B5C1F"),
    ),
    "THIRD_PARTY": dict(
        wordmark=None,  # populated per-document from the document's own "from_" org
        subtext=None,
        legal_name=None,
        address=[],
        rule_color=colors.HexColor("#555555"),
    ),
    "JOINT": dict(
        wordmark="NANDIRA RIVER BRIDGE PROJECT",
        subtext="Package NRB-4",
        legal_name=None,
        address=[],
        rule_color=colors.HexColor("#3A3A3A"),
    ),
}

CONFIDENTIALITY_TEXT = (
    "This document is issued in connection with Contract NHIA/NRB4/CW/2020-01 and is "
    "confidential to the Employer, Engineer, and Contractor and their permitted "
    "recipients. Not for distribution outside the Parties without the Employer's consent."
)

PROJECT_LINE = "Nandira River Bridge Project — Package NRB-4"

# ---------------------------------------------------------------------------
# Typography (Part A.15)
# ---------------------------------------------------------------------------
BODY_STYLE = ParagraphStyle(
    "Body", fontName=_BODY_FONT, fontSize=10.5, leading=13.6, alignment=TA_JUSTIFY,
    spaceAfter=6,
)
BULLET_STYLE = ParagraphStyle(
    "Bullet", parent=BODY_STYLE, leftIndent=12, bulletIndent=0, spaceAfter=4,
)
HEADING_STYLE = ParagraphStyle(
    "RunInHeading", fontName=_BODY_FONT_BOLD, fontSize=10.5, leading=13.6,
    spaceBefore=6, spaceAfter=4,
)
SUBHEADING_STYLE = ParagraphStyle(
    "SubHeading", fontName=_BODY_FONT_BOLD, fontSize=10, leading=12.5,
    spaceBefore=4, spaceAfter=2,
)
TITLE_STYLE = ParagraphStyle(
    "Title", fontName=_BODY_FONT_BOLD, fontSize=14, leading=17, alignment=TA_CENTER,
    spaceAfter=2,
)
SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle", fontName=_BODY_FONT, fontSize=10, leading=13, alignment=TA_CENTER,
    textColor=colors.HexColor("#444444"), spaceAfter=8,
)
SUBJECT_STYLE = ParagraphStyle(
    "Subject", fontName=_BODY_FONT_BOLD, fontSize=10.5, leading=13.6, spaceAfter=8,
)
META_LABEL_STYLE = ParagraphStyle("MetaLabel", fontName=_BODY_FONT_BOLD, fontSize=9, leading=11)
META_VALUE_STYLE = ParagraphStyle("MetaValue", fontName=_BODY_FONT, fontSize=9, leading=11)
SIGNATURE_STYLE = ParagraphStyle(
    "Signature", fontName=_BODY_FONT, fontSize=10.5, leading=14, spaceBefore=18,
)
TABLE_HEADER_STYLE = ParagraphStyle(
    "TableHeader", fontName=_BODY_FONT_BOLD, fontSize=9, leading=11, textColor=colors.white,
)
TABLE_CELL_STYLE = ParagraphStyle("TableCell", fontName=_BODY_FONT, fontSize=9, leading=11)
TABLE_CELL_RIGHT_STYLE = ParagraphStyle(
    "TableCellRight", parent=TABLE_CELL_STYLE, alignment=TA_RIGHT,
)
TABLE_CELL_BOLD_STYLE = ParagraphStyle("TableCellBold", fontName=_BODY_FONT_BOLD, fontSize=9.5, leading=12)
TABLE_CELL_BOLD_RIGHT_STYLE = ParagraphStyle(
    "TableCellBoldRight", parent=TABLE_CELL_BOLD_STYLE, alignment=TA_RIGHT,
)


def esc(text: str) -> str:
    """Escape a verbatim source string for safe embedding in a reportlab
    Paragraph (which uses a small XML-like markup). This changes no words -
    it only escapes the literal characters &, <, > so the renderer does not
    misinterpret them as markup."""
    return escape(text)


@dataclass
class DocumentSpec:
    doc_id: str
    title: str
    doc_type: str            # canonical DocumentType enum value
    doc_type_tag: str        # short label shown top-right of header band
    letterhead: str          # key into LETTERHEADS (or letterhead_registry, if given)
    letterhead_org_override: str | None = None  # for THIRD_PARTY: org name from doc text
    date: str = ""
    from_: str = ""
    to: str = ""
    cc: str | None = None
    contract_no: str = "NHIA/NRB4/CW/2020-01"
    extra_meta: list[tuple[str, str]] = field(default_factory=list)
    subject: str | None = None
    body: list[tuple[str, str]] = field(default_factory=list)  # ("heading"|"para"|"bullet", text)
    closing_lines: list[str] = field(default_factory=list)     # verbatim closing/signature lines
    scenario: int = 1
    # Independent-project overrides (Phase 4 Task 04 / Scenario 12): a
    # document belonging to a genuinely different project (different
    # Employer/Engineer/Contractor identities, different project name) sets
    # these two fields; every existing DocumentSpec across Scenarios 1-11
    # leaves them unset and renders byte-for-byte as before. project_line
    # replaces the module-level PROJECT_LINE constant in the title subtitle
    # and footer; letterhead_registry (shaped exactly like LETTERHEADS)
    # replaces the module-level LETTERHEADS lookup in the header. No
    # existing rendering path or output changes when these are left None.
    project_line: str | None = None
    letterhead_registry: dict | None = None


class _FooteredCanvas(canvas_module.Canvas):
    """Two-pass canvas so the footer can print 'Page n of N' (Part A.8),
    and so the confidentiality statement (Part A.13) is drawn once, on
    page 1 only."""

    def __init__(self, *args, doc_ctx=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states = []
        self._doc_ctx = doc_ctx

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        super().showPage()

    def save(self):
        total = len(self._saved_states) + 1
        # Re-run showPage() bookkeeping is not needed here since reportlab
        # already called showPage()/save() through BaseDocTemplate; instead
        # we hook via afterPage in the PageTemplate (see draw_header_footer).
        super().save()


def _draw_header(c, doc, spec: DocumentSpec):
    width, height = PAGE_SIZE
    top = height - MARGIN_TOP

    registry = spec.letterhead_registry or LETTERHEADS
    lh = registry[spec.letterhead]
    wordmark = lh["wordmark"] or (spec.letterhead_org_override or "")
    subtext = lh["subtext"] or ""
    rule_color = lh["rule_color"]

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(colors.black)
    c.drawString(MARGIN_LEFT, top - 2 * mm, wordmark)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#333333"))
    if subtext:
        c.drawString(MARGIN_LEFT, top - 7 * mm, subtext)

    legal_name = lh["legal_name"] or (spec.letterhead_org_override or "")
    addr_lines = lh["address"]
    y = top - 11.5 * mm
    c.setFont("Times-Roman", 8)
    c.setFillColor(colors.HexColor("#333333"))
    if legal_name and legal_name != wordmark:
        c.drawString(MARGIN_LEFT, y, legal_name)
        y -= 3.8 * mm
    for line in addr_lines:
        c.drawString(MARGIN_LEFT, y, line)
        y -= 3.8 * mm

    # Document Type Tag, top-right
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawRightString(width - MARGIN_RIGHT, top - 2 * mm, spec.doc_type_tag)

    # Header rule
    c.setStrokeColor(rule_color)
    c.setLineWidth(1.1)
    c.line(MARGIN_LEFT, top - HEADER_BAND_HEIGHT + 6 * mm, width - MARGIN_RIGHT, top - HEADER_BAND_HEIGHT + 6 * mm)


def _confidentiality_text(spec: DocumentSpec) -> str:
    """Same wording as the original fixed CONFIDENTIALITY_TEXT, parametrized
    on spec.contract_no instead of a hardcoded NRB4 contract number, so it
    reads correctly for a genuinely independent project (Scenario 12). Every
    existing DocumentSpec's contract_no already defaults to
    "NHIA/NRB4/CW/2020-01", so this produces the exact original text for
    Scenarios 1-11 with zero behavior change."""
    return (
        f"This document is issued in connection with Contract {spec.contract_no} and is "
        "confidential to the Employer, Engineer, and Contractor and their permitted "
        "recipients. Not for distribution outside the Parties without the Employer's consent."
    )


def _draw_footer(c, doc, spec: DocumentSpec, page_num: int, total_pages: int):
    width, _ = PAGE_SIZE
    bottom = MARGIN_BOTTOM

    project_line = spec.project_line or PROJECT_LINE

    c.setStrokeColor(colors.HexColor("#999999"))
    c.setLineWidth(0.4)
    c.line(MARGIN_LEFT, bottom + 6 * mm, width - MARGIN_LEFT, bottom + 6 * mm)

    c.setFont("Times-Roman", 8)
    c.setFillColor(colors.HexColor("#333333"))
    footer_text = f"{project_line}  |  {spec.doc_id}  |  Page {page_num} of {total_pages}"
    c.drawCentredString(width / 2, bottom + 2 * mm, footer_text)

    if page_num == 1:
        c.setFont("Times-Italic", 6.8)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawCentredString(width / 2, bottom - 2.2 * mm, _confidentiality_text(spec))


def _metadata_table(spec: DocumentSpec) -> Table:
    rows = [
        ["Document Reference:", spec.doc_id],
        ["Date:", spec.date],
        ["Contract No.:", spec.contract_no],
        ["From:", spec.from_],
        ["To:", spec.to],
    ]
    if spec.cc:
        rows.append(["CC:", spec.cc])
    for label, value in spec.extra_meta:
        rows.append([f"{label}:", value])

    data = [
        [Paragraph(esc(label), META_LABEL_STYLE), Paragraph(esc(value), META_VALUE_STYLE)]
        for label, value in rows
    ]
    tbl = Table(data, colWidths=[32 * mm, None])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ]
        )
    )
    return tbl


def _build_table(table_spec: dict) -> Table:
    """Render a ('table', {...}) body block. `headers` (optional list of
    strings) and every cell in `rows` are the caller's verbatim source
    text/numbers -- this only lays them out in a grid instead of
    space-padded plain text (which does not align in a proportional font).
    `right_align_cols` (set of column indices) right-aligns numeric/amount
    columns. `bold_last_row` bolds a closing total/summary row."""
    headers = table_spec.get("headers")
    rows = table_spec["rows"]
    right_cols = set(table_spec.get("right_align_cols", []))
    bold_last_row = table_spec.get("bold_last_row", False)
    col_widths = table_spec.get("col_widths")

    data = []
    if headers:
        data.append(
            [Paragraph(esc(str(h)), TABLE_HEADER_STYLE) for h in headers]
        )
    n_rows = len(rows)
    for r_idx, row in enumerate(rows):
        is_bold = bold_last_row and r_idx == n_rows - 1
        cells = []
        for c_idx, cell in enumerate(row):
            if c_idx in right_cols:
                style = TABLE_CELL_BOLD_RIGHT_STYLE if is_bold else TABLE_CELL_RIGHT_STYLE
            else:
                style = TABLE_CELL_BOLD_STYLE if is_bold else TABLE_CELL_STYLE
            cells.append(Paragraph(esc(str(cell)), style))
        data.append(cells)

    tbl = Table(data, colWidths=col_widths, repeatRows=1 if headers else 0)
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if headers:
        style_cmds.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3A3A3A")))
    if bold_last_row:
        last = len(data) - 1
        style_cmds.append(("LINEABOVE", (0, last), (-1, last), 1.0, colors.black))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _body_flowables(spec: DocumentSpec) -> list:
    flowables = []
    for kind, text in spec.body:
        if kind == "table":
            flowables.append(Spacer(1, 2 * mm))
            flowables.append(_build_table(text))
            flowables.append(Spacer(1, 2 * mm))
            continue
        safe = esc(text)
        if kind == "heading":
            flowables.append(Paragraph(safe, HEADING_STYLE))
        elif kind == "subheading":
            flowables.append(Paragraph(safe, SUBHEADING_STYLE))
        elif kind == "bullet":
            flowables.append(Paragraph(f"&bull;&nbsp;&nbsp;{safe}", BULLET_STYLE))
        elif kind == "total_box":
            flowables.append(Spacer(1, 1.5 * mm))
            box = Table([[Paragraph(safe, ParagraphStyle(
                "TotalBox", fontName=_BODY_FONT_BOLD, fontSize=11.5, leading=14,
            ))]], colWidths=[None])
            box.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1.1, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            flowables.append(box)
            flowables.append(Spacer(1, 1.5 * mm))
        else:  # "para"
            flowables.append(Paragraph(safe, BODY_STYLE))
    return flowables


def _signature_flowables(spec: DocumentSpec) -> list:
    flowables = [Spacer(1, 4 * mm)]
    for line in spec.closing_lines:
        flowables.append(Paragraph(esc(line), SIGNATURE_STYLE if line == spec.closing_lines[0] else BODY_STYLE))
    return flowables


def render_document(spec: DocumentSpec, out_path: str) -> None:
    """Render one DocumentSpec to a PDF at out_path, using the Dataset V2
    template system. No content in `spec` is altered here."""

    frame = Frame(
        MARGIN_LEFT,
        MARGIN_BOTTOM + FOOTER_BAND_HEIGHT,
        PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT,
        PAGE_SIZE[1] - MARGIN_TOP - HEADER_BAND_HEIGHT - MARGIN_BOTTOM - FOOTER_BAND_HEIGHT,
        id="body",
        topPadding=0,
        bottomPadding=0,
    )

    def on_page(c, doc_):
        _draw_header(c, doc_, spec)
        # Footer with correct total page count is drawn in a second pass below.

    template = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc = BaseDocTemplate(
        out_path,
        pagesize=PAGE_SIZE,
        pageTemplates=[template],
        title=spec.title,
        author=spec.from_,
        subject=spec.subject or spec.doc_type,
    )

    story = []
    story.append(Paragraph(esc(spec.title), TITLE_STYLE))
    story.append(Paragraph(esc(spec.project_line or PROJECT_LINE), SUBTITLE_STYLE))
    story.append(_metadata_table(spec))
    story.append(Spacer(1, 4 * mm))
    if spec.subject:
        story.append(Paragraph(f"<b>Subject:</b> {esc(spec.subject)}", SUBJECT_STYLE))
    story.extend(_body_flowables(spec))
    story.extend(_signature_flowables(spec))

    doc.build(story)

    # --- second pass: stamp footers with correct "Page n of N" -------------
    _stamp_footers(out_path, spec)


def _stamp_footers(pdf_path: str, spec: DocumentSpec) -> None:
    """reportlab does not know the final page count while building flowables
    page-by-page, so footers (which must show 'Page n of N') are stamped in
    a lightweight second pass using pypdf, after the true page count is
    known. This touches only the footer band already reserved as blank
    margin space - it does not alter body content."""
    from pypdf import PdfReader, PdfWriter
    import io

    reader = PdfReader(pdf_path)
    total = len(reader.pages)

    overlay_bytes_per_page = []
    for i in range(total):
        buf = io.BytesIO()
        c = canvas_module.Canvas(buf, pagesize=PAGE_SIZE)
        _draw_footer(c, None, spec, i + 1, total)
        c.save()
        buf.seek(0)
        overlay_bytes_per_page.append(PdfReader(buf).pages[0])

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        page.merge_page(overlay_bytes_per_page[i])
        writer.add_page(page)

    with open(pdf_path, "wb") as f:
        writer.write(f)
