from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml
import re
from pathlib import Path
from typing import Dict, Optional, List
import io


# ============================================================
# Document design tokens
#
# Every visual property of the generated proposal is defined here so the
# cover page, headers, footers, body text and tables stay consistent.
# Changing a value here changes it everywhere in the document.
# ============================================================

COMPANY_NAME = "63SATS"
COMPANY_LEGAL_NAME = "63SATS Cybertech Limited"
CONFIDENTIALITY_NOTICE = "Confidential & Proprietary — 63SATS Cybertech Limited"

# Fonts, sizes and colours are taken from the reference template
# (template.docx). Myriad Pro is the 63SATS corporate face; machines without
# it fall back to a Word substitute, so change BODY_FONT if that matters.
BODY_FONT = "Myriad Pro"
HEADING_FONT = "Myriad Pro"

BODY_SIZE = Pt(10)
TITLE_SIZE = Pt(50)
SUBTITLE_SIZE = Pt(24)
H1_SIZE = Pt(20)
H2_SIZE = Pt(14)
H3_SIZE = Pt(12)
TABLE_SIZE = Pt(10)
HEADER_FOOTER_SIZE = Pt(9)

BRAND_COLOR = RGBColor(0x11, 0x2E, 0x54)      # #112E54 headings, cover title
ACCENT_COLOR = RGBColor(0x1A, 0x3A, 0x5C)     # #1A3A5C sub-headings, labels
MUTED_COLOR = RGBColor(0x59, 0x59, 0x59)      # footer text
BRAND_FILL = "112E54"                          # table header shading (hex, no #)
RULE_COLOR = "45A2DD"                          # accent bars and rules
ACCENT_BAR_COLOR = "45A2DD"                    # #45A2DD bar left of headings

# A4, matching the branded page-frame artwork lifted from template.docx.
PAGE_WIDTH = Inches(8.27)
PAGE_HEIGHT = Inches(11.69)
MARGIN_TOP = Inches(1.35)      # clears the 63 shield in the frame artwork
MARGIN_BOTTOM = Inches(1.15)   # clears the decorative footer band
MARGIN_SIDE = Inches(0.9)

PAGE_FRAME_IMAGE = Path(__file__).resolve().parent.parent / "assets" / "63sats_page_frame.png"

LINE_SPACING = 1.15
PARA_SPACE_AFTER = Pt(6)
LIST_INDENT = Inches(0.25)


def _set_style_font(style, name: str, size=None, bold=None, color=None,
                    italic=None):
    """Pin a style's font across ascii/hAnsi/eastAsia/cs so Word cannot
    substitute a different face for parts of a run."""
    font = style.font
    font.name = name
    if size is not None:
        font.size = size
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic
    if color is not None:
        font.color.rgb = color

    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rfonts.set(qn(attr), name)
    # Drop any theme-font reference inherited from the base template,
    # otherwise the theme wins over the explicit font above.
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]


def _apply_run_font(run, name=BODY_FONT, size=BODY_SIZE, bold=None,
                    italic=None, color=None):
    """Force an explicit font on a run. Used for every run we create so that
    text coming from AI extraction or user edits cannot carry drift."""
    run.font.name = name
    run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color

    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rfonts.set(qn(attr), name)


def _configure_page(doc):
    """A4 page and margins sized to clear the branded frame artwork."""
    for section in doc.sections:
        section.page_width = PAGE_WIDTH
        section.page_height = PAGE_HEIGHT
        section.top_margin = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM
        section.left_margin = MARGIN_SIDE
        section.right_margin = MARGIN_SIDE
        section.header_distance = Inches(0.3)
        section.footer_distance = Inches(0.75)


def _add_page_frame(header_part):
    """Place the 63SATS branded page artwork behind the text of every page.

    python-docx can only add a picture inline, so the resulting <wp:inline>
    is rewritten as a floating <wp:anchor> pinned to the page origin with
    behindDoc="1" — the same construction the reference template uses.
    """
    if not PAGE_FRAME_IMAGE.exists():
        return None

    paragraph = _clear_paragraph(header_part.paragraphs[0])
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run()
    run.add_picture(str(PAGE_FRAME_IMAGE), width=PAGE_WIDTH, height=PAGE_HEIGHT)

    inline = run._element.find(qn('w:drawing'))[0]
    anchor = parse_xml(
        '<wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/'
        '2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0" '
        'simplePos="0" relativeHeight="0" behindDoc="1" locked="0" '
        'layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset>'
        '</wp:positionH>'
        '<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset>'
        '</wp:positionV>'
        '</wp:anchor>')

    # Carry the sizing and the picture itself over from the inline element.
    for tag in ('wp:extent', 'wp:effectExtent', 'wp:docPr',
                'wp:cNvGraphicFramePr'):
        child = inline.find(qn(tag))
        if child is not None:
            anchor.append(child)
        elif tag == 'wp:effectExtent':
            anchor.append(parse_xml(
                '<wp:effectExtent xmlns:wp="http://schemas.openxmlformats.org/'
                'drawingml/2006/wordprocessingDrawing" l="0" t="0" r="0" '
                'b="0"/>'))

    # wrapNone has to sit between the frame properties and the graphic.
    wrap = parse_xml(
        '<wp:wrapNone xmlns:wp="http://schemas.openxmlformats.org/drawingml/'
        '2006/wordprocessingDrawing"/>')
    doc_pr = anchor.find(qn('wp:docPr'))
    if doc_pr is not None:
        doc_pr.addprevious(wrap)
    else:
        anchor.append(wrap)

    graphic = inline.find(
        qn('a:graphic') if inline.find(qn('a:graphic')) is not None
        else '{http://schemas.openxmlformats.org/drawingml/2006/main}graphic')
    if graphic is not None:
        anchor.append(graphic)

    inline.getparent().replace(inline, anchor)
    return paragraph


def _add_accent_bar(paragraph, color=ACCENT_BAR_COLOR, size=24):
    """Thick vertical rule to the left of a heading, as in the template."""
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn('w:pBdr'))
    if borders is None:
        borders = OxmlElement('w:pBdr')
        p_pr.append(borders)
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single')
    left.set(qn('w:sz'), str(size))
    left.set(qn('w:space'), '8')
    left.set(qn('w:color'), color)
    borders.append(left)


def _configure_styles(doc):
    """Define the document's style set once, up front.

    python-docx's default template bases headings on Calibri Light with a
    theme colour, which is why headings and body text used to disagree.
    Every style used by the generator is pinned explicitly here.
    """
    styles = doc.styles

    normal = styles['Normal']
    _set_style_font(normal, BODY_FONT, BODY_SIZE)
    normal.paragraph_format.space_after = PARA_SPACE_AFTER
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = LINE_SPACING

    heading_specs = [
        ('Title', TITLE_SIZE, True, BRAND_COLOR, Pt(0), Pt(6)),
        ('Heading 1', H1_SIZE, True, BRAND_COLOR, Pt(18), Pt(8)),
        ('Heading 2', H2_SIZE, True, ACCENT_COLOR, Pt(12), Pt(6)),
        ('Heading 3', H3_SIZE, True, ACCENT_COLOR, Pt(10), Pt(4)),
    ]
    for name, size, bold, color, before, after in heading_specs:
        try:
            style = styles[name]
        except KeyError:
            continue
        _set_style_font(style, HEADING_FONT, size, bold=bold, color=color)
        style.paragraph_format.space_before = before
        style.paragraph_format.space_after = after
        style.paragraph_format.line_spacing = LINE_SPACING
        style.paragraph_format.keep_with_next = True

    for name, size, color in (('Header', HEADER_FOOTER_SIZE, MUTED_COLOR),
                              ('Footer', HEADER_FOOTER_SIZE, MUTED_COLOR),
                              ('Caption', Pt(9), MUTED_COLOR)):
        try:
            style = styles[name]
        except KeyError:
            continue
        _set_style_font(style, BODY_FONT, size, color=color)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.0


def _clear_paragraph(paragraph):
    """Strip every run from a paragraph.

    Preferred over `paragraph.text = ""`, which leaves behind an empty,
    unstyled run that would pick up the theme font.
    """
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)
    return paragraph


def _add_bottom_border(paragraph, color=RULE_COLOR, size=6):
    """Thin rule under a paragraph (used for the header and cover page)."""
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(size))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    borders.append(bottom)
    p_pr.append(borders)


def _add_field(paragraph, instruction: str, placeholder: str = "1"):
    """Insert a Word field (PAGE, NUMPAGES) that updates on open/print."""
    run = paragraph.add_run()
    _apply_run_font(run, BODY_FONT, HEADER_FOOTER_SIZE, color=MUTED_COLOR)

    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = f' {instruction} '
    separate = OxmlElement('w:fldChar')
    separate.set(qn('w:fldCharType'), 'separate')
    text = OxmlElement('w:t')
    text.text = placeholder
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')

    for element in (begin, instr, separate, text, end):
        run._r.append(element)
    return run


def _configure_header_footer(doc):
    """Branded frame on every page, page number in the footer.

    Matches the reference template, whose headers carry only the artwork and
    whose footers carry only the page number.
    """
    section = doc.sections[0]
    section.different_first_page_header_footer = True

    # The frame goes on the cover page and on every body page.
    _add_page_frame(section.first_page_header)
    _add_page_frame(section.header)

    for paragraph in section.first_page_footer.paragraphs:
        _clear_paragraph(paragraph)

    # Page number only, right-aligned and lifted clear of the footer band.
    footer_para = _clear_paragraph(section.footer.paragraphs[0])
    footer_para.style = doc.styles['Footer']
    footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _add_field(footer_para, "PAGE", "1")


def _add_heading(doc, text: str, level: int = 1, page_break: bool = False):
    """Heading in the template's style: navy, bold, accent bar on level 1.

    `page_break` starts the heading on a fresh page, which is how the
    reference template separates its top-level sections.
    """
    heading = doc.add_heading(text, level=level)
    sizes = {0: TITLE_SIZE, 1: H1_SIZE, 2: H2_SIZE, 3: H3_SIZE}
    colors = {0: BRAND_COLOR, 1: BRAND_COLOR, 2: ACCENT_COLOR, 3: ACCENT_COLOR}
    for run in heading.runs:
        _apply_run_font(run, HEADING_FONT, sizes.get(level, H3_SIZE),
                        bold=True, color=colors.get(level, ACCENT_COLOR))

    if level == 1:
        _add_accent_bar(heading)
        heading.paragraph_format.left_indent = Inches(0.12)
    if page_break:
        heading.paragraph_format.page_break_before = True
        heading.paragraph_format.space_before = Pt(0)
    return heading


def _pin_default_font(doc):
    """Make the document's *default* font Myriad Pro too.

    Individual runs are already pinned, but docDefaults and the theme still
    carry Word's stock fonts — so any text typed into the document after
    generation would come out in the wrong face. This closes that gap.
    """
    # docDefaults/rPrDefault
    styles_el = doc.styles.element
    doc_defaults = styles_el.find(qn('w:docDefaults'))
    if doc_defaults is not None:
        rpr_default = doc_defaults.find(qn('w:rPrDefault'))
        if rpr_default is not None:
            rpr = rpr_default.find(qn('w:rPr'))
            if rpr is None:
                rpr = OxmlElement('w:rPr')
                rpr_default.append(rpr)
            rfonts = rpr.find(qn('w:rFonts'))
            if rfonts is None:
                rfonts = OxmlElement('w:rFonts')
                rpr.insert(0, rfonts)
            for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme',
                         'w:cstheme'):
                if rfonts.get(qn(attr)) is not None:
                    del rfonts.attrib[qn(attr)]
            for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                rfonts.set(qn(attr), BODY_FONT)

    # Theme major/minor fonts, which styles fall back to.
    try:
        theme = doc.part.package.part_related_by  # presence check only
    except AttributeError:  # pragma: no cover - defensive
        return
    for part in doc.part.package.iter_parts():
        if not str(part.partname).endswith('theme1.xml'):
            continue
        xml = part.blob.decode('utf-8')
        xml = re.sub(r'(<a:latin typeface=")[^"]*(")',
                     r'\g<1>' + BODY_FONT + r'\g<2>', xml)
        part._blob = xml.encode('utf-8')


def _enable_field_update(doc):
    """Ask Word to refresh fields (the TOC, page counts) when opening."""
    settings = doc.settings.element
    if settings.find(qn('w:updateFields')) is None:
        update = OxmlElement('w:updateFields')
        update.set(qn('w:val'), 'true')
        settings.append(update)


def _add_toc(doc, nums=None):
    """Index page carrying a Word TOC field over heading levels 1-2."""
    _add_heading(doc, 'Index', 1, page_break=True)

    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    _apply_run_font(run, BODY_FONT, BODY_SIZE)

    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = r' TOC \o "1-2" \h \z \u '
    separate = OxmlElement('w:fldChar')
    separate.set(qn('w:fldCharType'), 'separate')
    placeholder = OxmlElement('w:t')
    placeholder.text = ('Right-click and choose "Update Field" to build the '
                        'table of contents.')
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')

    for element in (begin, instr, separate, placeholder, end):
        run._r.append(element)
    return paragraph


class _Numbering:
    """Hands out section numbers as headings are emitted.

    Sections are numbered by position, so inserting or reordering a section
    never requires renumbering the ones around it.
    """

    def __init__(self):
        self.section = 0
        self.sub = 0

    def section_title(self, title: str) -> str:
        self.section += 1
        self.sub = 0
        return f"{self.section}. {title}"

    def sub_title(self, title: str) -> str:
        self.sub += 1
        return f"{self.section}.{self.sub} {title}"


def _section(doc, nums: _Numbering, title: str):
    """Top-level numbered section, starting on a new page."""
    return _add_heading(doc, nums.section_title(title), 1, page_break=True)


def _subsection(doc, nums: _Numbering, title: str):
    """Numbered subsection under the current section."""
    return _add_heading(doc, nums.sub_title(title), 2)


def _add_paragraph(doc, text: str = "", bold=False, italic=False, size=BODY_SIZE,
                   color=None, align=None, indent=None, space_after=None):
    """Body paragraph with an explicitly pinned font."""
    paragraph = doc.add_paragraph()
    if align is not None:
        paragraph.alignment = align
    if indent is not None:
        paragraph.paragraph_format.left_indent = indent
    if space_after is not None:
        paragraph.paragraph_format.space_after = space_after
    if text:
        run = paragraph.add_run(text)
        _apply_run_font(run, BODY_FONT, size, bold=bold, italic=italic,
                        color=color)
    return paragraph


BULLET_RE = re.compile(r'^([\u2022\u25cf\u25aa*\-o])\s+(.*)$')
NUMBERED_RE = re.compile(r'^(\d+[\.\)])\s+(.*)$')
TABLE_ROW_RE = re.compile(r'^\|.*\|$')
TABLE_SEPARATOR_RE = re.compile(r'^\|[\s:\-\|]+\|$')


def _add_list_item(doc, marker: str, text: str, depth: int = 0):
    """List item rendered with a literal marker and a hanging indent.

    Deliberately not Word's List Bullet/List Number styles: those renumber
    themselves across the document and would desynchronise the numbering that
    already exists inside extracted content.
    """
    paragraph = doc.add_paragraph()
    fmt = paragraph.paragraph_format
    indent = LIST_INDENT * (depth + 1)
    # Hanging indent with a tab stop at the text position, so wrapped lines
    # line up under the text rather than under the marker.
    fmt.left_indent = indent + Inches(0.25)
    fmt.first_line_indent = -Inches(0.25)
    fmt.space_after = Pt(2)
    fmt.tab_stops.add_tab_stop(indent + Inches(0.25), WD_TAB_ALIGNMENT.LEFT)
    run = paragraph.add_run(f"{marker}	{text}")
    _apply_run_font(run, BODY_FONT, BODY_SIZE)
    return paragraph


def _cell_paragraph(cell):
    """First paragraph of a cell with any pre-existing runs removed.

    Avoids the empty, unstyled run that `cell.text = ""` leaves behind —
    that run would carry the theme font if someone later types into the cell.
    """
    return _clear_paragraph(cell.paragraphs[0])


def _add_table(doc, rows: List[List[str]], header: bool = True,
               widths: Optional[List[float]] = None):
    """Table with consistent grid, shaded repeating header row and body font."""
    if not rows:
        return None

    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, row_data in enumerate(rows):
        row = table.rows[i]
        is_header = header and i == 0
        if is_header:
            # Repeat the header row when the table spans a page break.
            tr_pr = row._tr.get_or_add_trPr()
            tbl_header = OxmlElement('w:tblHeader')
            tbl_header.set(qn('w:val'), 'true')
            tr_pr.append(tbl_header)

        for j in range(cols):
            cell = row.cells[j]
            paragraph = _cell_paragraph(cell)
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.paragraph_format.line_spacing = 1.0
            value = row_data[j] if j < len(row_data) else ""
            run = paragraph.add_run(value)
            _apply_run_font(
                run, BODY_FONT, TABLE_SIZE, bold=is_header,
                color=RGBColor(0xFF, 0xFF, 0xFF) if is_header else None)

            if is_header:
                shading = OxmlElement('w:shd')
                shading.set(qn('w:val'), 'clear')
                shading.set(qn('w:fill'), BRAND_FILL)
                cell._tc.get_or_add_tcPr().append(shading)

    if widths:
        table.autofit = False
        for row in table.rows:
            for idx, width in enumerate(widths[:cols]):
                row.cells[idx].width = Inches(width)

    return table


def _set_table_width(table, width_inches: float):
    """Pin a table's total width so `alignment` actually centres it."""
    tbl_pr = table._tbl.tblPr
    existing = tbl_pr.find(qn('w:tblW'))
    if existing is not None:
        tbl_pr.remove(existing)
    tbl_w = OxmlElement('w:tblW')
    tbl_w.set(qn('w:type'), 'dxa')
    tbl_w.set(qn('w:w'), str(int(Inches(width_inches).twips)))
    tbl_pr.append(tbl_w)


def _parse_markdown_table(lines: List[str]) -> List[List[str]]:
    """Turn `| a | b |` pipe rows into cell lists, dropping the `|---|` rule."""
    rows = []
    for line in lines:
        if TABLE_SEPARATOR_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    return rows


def _looks_like_label(line: str, next_line: Optional[str]) -> bool:
    """Short, unpunctuated line acting as an inline sub-heading inside a
    block of extracted text (e.g. 'Risk Register', 'Client Dependencies')."""
    if len(line) > 60 or line.endswith(('.', ',', ';', ':')):
        return False
    if BULLET_RE.match(line) or NUMBERED_RE.match(line):
        return False
    return next_line is None or not next_line.strip() or bool(
        BULLET_RE.match(next_line.strip()))


def _add_body_text(doc, text):
    """Render a block of text with consistent typography.

    Handles the shapes that show up in both the hardcoded defaults and in
    AI-extracted values: bullets, numbered items, indented sub-bullets,
    markdown pipe tables and short label lines.
    """
    if text is None:
        return
    lines = str(text).replace('\r\n', '\n').replace('\r', '\n').split('\n')

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        # Markdown table -> real Word table
        if TABLE_ROW_RE.match(line):
            table_lines = []
            while i < len(lines) and TABLE_ROW_RE.match(lines[i].strip()):
                table_lines.append(lines[i].strip())
                i += 1
            rows = _parse_markdown_table(table_lines)
            _add_table(doc, rows, header=True)
            _add_paragraph(doc, space_after=Pt(4))
            continue

        indent = len(raw) - len(raw.lstrip())
        depth = 1 if indent >= 3 else 0

        bullet = BULLET_RE.match(line)
        if bullet:
            _add_list_item(doc, "\u2022", bullet.group(2), depth)
            i += 1
            continue

        numbered = NUMBERED_RE.match(line)
        if numbered:
            _add_list_item(doc, numbered.group(1), numbered.group(2), depth)
            i += 1
            continue

        next_line = lines[i + 1] if i + 1 < len(lines) else None
        if _looks_like_label(line, next_line):
            _add_paragraph(doc, line, bold=True, color=ACCENT_COLOR,
                           space_after=Pt(3))
            i += 1
            continue

        _add_paragraph(doc, line)
        i += 1


def _add_cover_page(doc, extracted_data: Dict, client_name: str,
                    project_title: str):
    """Fixed-layout cover page, identical for every generated proposal."""
    _add_paragraph(doc, space_after=Pt(48))

    brand = doc.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.CENTER
    brand.paragraph_format.space_after = Pt(0)
    brand_run = brand.add_run(COMPANY_NAME)
    _apply_run_font(brand_run, HEADING_FONT, TITLE_SIZE, bold=True,
                    color=BRAND_COLOR)

    tagline = doc.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tagline.paragraph_format.space_after = Pt(10)
    tagline_run = tagline.add_run(COMPANY_LEGAL_NAME)
    _apply_run_font(tagline_run, BODY_FONT, Pt(11), color=MUTED_COLOR)
    _add_bottom_border(tagline, size=12)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_before = Pt(24)
    subtitle.paragraph_format.space_after = Pt(4)
    subtitle_run = subtitle.add_run(project_title)
    _apply_run_font(subtitle_run, HEADING_FONT, SUBTITLE_SIZE, bold=True,
                    color=BRAND_COLOR)

    prepared = doc.add_paragraph()
    prepared.alignment = WD_ALIGN_PARAGRAPH.CENTER
    prepared.paragraph_format.space_after = Pt(48)
    prepared_run = prepared.add_run(f"Prepared for {client_name}")
    _apply_run_font(prepared_run, BODY_FONT, Pt(12), color=MUTED_COLOR)

    details = [
        ("Submitted to", client_name),
        ("Attention", extracted_data.get('contact_person', 'Mr. XXXXXXX XXXXX')),
        ("Submitted by", extracted_data.get('submitted_by', '63SATS Team')),
        ("Date", extracted_data.get('date', '23rd May 2026')),
        ("Proposal No", extracted_data.get('proposal_no', 'CR-XXXX-2026')),
    ]

    table = doc.add_table(rows=len(details), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_table_width(table, 5.6)
    for row_idx, (label, value) in enumerate(details):
        cells = table.rows[row_idx].cells
        cells[0].width = Inches(1.6)
        cells[1].width = Inches(4.0)
        for cell, content, is_label in ((cells[0], label, True),
                                        (cells[1], str(value), False)):
            paragraph = _cell_paragraph(cell)
            paragraph.paragraph_format.space_after = Pt(3)
            paragraph.paragraph_format.line_spacing = 1.0
            run = paragraph.add_run(content)
            _apply_run_font(run, BODY_FONT, Pt(11), bold=is_label,
                            color=ACCENT_COLOR if is_label else None)

    footer_note = doc.add_paragraph()
    footer_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_note.paragraph_format.space_before = Pt(48)
    note_run = footer_note.add_run(CONFIDENTIALITY_NOTICE)
    _apply_run_font(note_run, BODY_FONT, Pt(9), italic=True, color=MUTED_COLOR)

    # End the cover page; body content starts on page 2.
    break_paragraph = doc.add_paragraph()
    break_run = break_paragraph.add_run()
    _apply_run_font(break_run)
    break_run.add_break(WD_BREAK.PAGE)


# Fixed content for 63SATS proposals (same for all)
ABOUT_63SATS = """63SATS, driven by the innovative technology of 63 moons technologies ltd., stands as a comprehensive cybersecurity solutions provider catering to the needs of enterprises. Renowned as trailblazers in both digital markets and cybersecurity, we specialize in ensuring top-notch security for Enterprises, Industries & Government sectors.

63SATS brings you internationally recognized products and manages services with a mission to safeguard invaluable assets against the entire spectrum of sophisticated cyber threats. To position our clients as leading models of secure digital entities in India and globally, 63SATS Cybertech Limited as a security consulting & solution providing company has forged strategic partnerships with top-tier security product companies across the globe."""


WHY_63SATS = """63SATS is the right partner for this engagement because:

1. Expertise
   • Team of certified cybersecurity professionals (CISSP, CISM, CEH, OSCP)
   • Extensive experience with enterprise security implementations
   • Continuous training and knowledge development
   • Deep expertise across multiple security domains

2. Partnership & Technology
   • Relationships with leading technology vendors
   • Vendor-neutral approach to recommend best-fit solutions
   • Direct access to vendor engineering and support teams
   • Joint go-to-market capabilities

3. Customer Focus
   • Dedicated account management
   • Customized service delivery aligned to your needs
   • Flexible engagement models
   • Proven track record with similar organizations
   • Transparent communication and regular updates

4. Technology Leadership
   • Cloud-native platform expertise
   • Integration with existing tools and workflows
   • Continuous platform optimization
   • Access to emerging security capabilities

5. Value Proposition
   • Competitive and transparent pricing
   • No hidden fees or surprise charges
   • Predictable cost structure (OpEx vs CapEx)
   • Measurable outcomes and ROI
   • Commitment to customer success"""


DOCUMENT_CONTROL = """This proposal document and all its contents, including but not limited to text, graphics, logos, methodologies, processes, and pricing structures, are the exclusive property of 63SATS (hereinafter referred to as "the Company").

The recipient of this document (hereinafter referred to as "the Client") is granted a limited, non-transferable license to review this proposal solely for the purpose of evaluating the services offered. The Client agrees not to:

• Reproduce, distribute, or transmit this document in any form without prior written consent from 63SATS
• Disclose any proprietary information, methodologies, or pricing to third parties
• Use any concepts, frameworks, or approaches described herein for purposes other than engagement with 63SATS
• Reverse engineer or attempt to derive source methodologies from the proposed solutions

All intellectual property rights, including trademarks, service marks, and trade secrets contained in this proposal, remain the sole property of 63SATS. Any unauthorized use, reproduction, or distribution may result in legal action.

This proposal is valid for a period of 30 days from the date of issuance unless otherwise specified in writing."""


RISK_TEMPLATE = """The following risk assessment identifies potential risks to the successful delivery of managed services and outlines mitigation strategies to minimize impact.

Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Access delays | High | Medium | Early engagement with client IT team |
| Scope changes | Medium | High | Change control process with documentation |
| Resource constraints | Medium | Low | 63SATS has backup resources available |
| Vendor dependencies | Medium | Low | Multi-vendor relationships |

Risk Monitoring & Review

Risk management is an ongoing process throughout the engagement:

• Monthly Risk Review: Assessment of identified risks and identification of new risks
• Quarterly Risk Report: Comprehensive risk status report to stakeholders
• Incident-Based Review: Post-incident analysis to identify new risks or control gaps
• Continuous Monitoring: Real-time monitoring of critical risk indicators

Business Continuity & Disaster Recovery

In the event of a major incident or disaster, the following procedures will be activated:

• Incident Declaration: Clear criteria for declaring a disaster or major incident
• Communication Plan: Immediate notification to client stakeholders and 63SATS management
• Recovery Procedures: Documented steps for system recovery and restoration
• Escalation Path: Direct escalation to vendor support for critical issues
• Backup Restoration: Process for restoring configurations from backup
• Post-Incident Review: Comprehensive analysis and lessons learned documentation"""


# ============================================================
# Section content carried over from template.docx
# ============================================================

TRANSITION_APPROACH = """The transition to 63SATS managed services will follow a structured approach to ensure seamless knowledge transfer and minimal disruption to your existing operations.

Phase 1: Kick-off, access provisioning and documentation review
Phase 2: Knowledge transfer, SOC onboarding and runbook creation
Phase 3: Shadow operations, validation and go-live preparation
Steady State: Full 24/7 operations, regular reporting and continuous improvement"""

TRANSITION_TIMELINE_TABLE = [
    ['Phase', 'Timeline', 'Activities'],
    ['Phase 1', 'Month 1', 'Kick-off, access provisioning, documentation review'],
    ['Phase 2', 'Month 2', 'Knowledge transfer, SOC onboarding, runbook creation'],
    ['Phase 3', 'Month 3', 'Shadow operations, validation, go-live preparation'],
    ['Steady State', 'Month 4 onwards', 'Full 24/7 operations, regular reporting, continuous improvement'],
    ['Optional Migration', 'TBD by Client', 'Platform migration (separate SOW)'],
]

OPERATIONAL_ACTIVITIES_INTRO = "Post-transition, 63SATS will execute the following operational activities:"

DAILY_OPERATIONS = """• 24/7 monitoring and incident response
• Health status verification of all managed devices
• Alert triage and initial response
• Daily status reports to designated contacts"""

WEEKLY_ACTIVITIES = """• Weekly performance and health reports
• Rule optimization recommendations
• Change request review and scheduling
• Stakeholder status calls"""

MONTHLY_ACTIVITIES = """• Comprehensive security posture reports
• Policy compliance audits
• Capacity and performance trending
• Service review meetings"""

QUARTERLY_ACTIVITIES = """• Quarterly business reviews (QBR)
• Strategic security recommendations
• Patch and upgrade planning
• SLA performance review"""

OPTIONAL_MIGRATION = """During the contract period, the client may opt for one-time migration services to modernize the managed platform. Options include:

• Migration to a cloud-native management platform
• Migration to a hyperconverged infrastructure deployment

The scope, timeline, and commercial terms for optional migration will be defined in a separate Statement of Work (SOW) upon client decision to proceed."""

CLIENT_DEPENDENCIES_TABLE = [
    ['Dependency', 'Impact if Not Met', 'Mitigation'],
    ['Timely access provisioning', 'Delayed service commencement', 'Include in kick-off checklist'],
    ['Change approval responsiveness', 'Delayed implementations, SLA impact', 'Define escalation matrix'],
    ['Accurate network documentation', 'Incorrect troubleshooting, longer MTTR', 'Discovery phase validation'],
    ['License renewals on time', 'Service interruption due to license expiry', 'Renewal tracking and reminders'],
]

SATS_DEPENDENCIES_TABLE = [
    ['Dependency', 'Impact if Not Met', 'Mitigation'],
    ['SOC team availability', 'Service coverage gaps', 'Cross-training, backup resources'],
    ['Tool/platform availability', 'Monitoring and management gaps', 'Redundant tooling, SLA with vendors'],
    ['Vendor support', 'Extended resolution for complex issues', 'Premium support contracts'],
    ['Knowledge transfer completion', 'Operational inefficiencies', 'Structured KT plan, documentation'],
    ['Runbook development', 'Inconsistent procedures', 'Template-based approach, peer review'],
]

EXTERNAL_DEPENDENCIES_TABLE = [
    ['Dependency', 'Description', 'Owner'],
    ['Vendor TAC Support', 'Technical support for complex issues and bug fixes', 'OEM'],
    ['Cloud Provider', 'Infrastructure availability for cloud-deployed workloads', 'Cloud provider'],
    ['Internet Service Providers', 'Connectivity at all locations', 'Various ISPs'],
    ['Threat Intelligence Feeds', 'Up-to-date threat information for proactive defense', 'Third-party providers'],
    ['Patch Availability', 'Timely release of security patches', 'OEM'],
]

CRITICAL_PATH_DEPENDENCIES = """The following dependencies are on the critical path for service commencement and must be resolved before go-live:

• VPN and management console access provisioning — required for remote monitoring and management
• Administrative credentials for all in-scope devices — required for configuration management
• Change approval workflow definition — required for structured change management
• Escalation matrix and contact information — required for incident response
• Current configuration backup — required as rollback baseline
• License validation — required to ensure uninterrupted service"""

RISK_HEAT_MAP_TABLE = [
    ['Risk Level', 'Count', 'Primary Mitigation Approach'],
    ['Critical Risk', '2', '24/7 monitoring, incident response plan, threat intelligence integration'],
    ['High Risk', '4', 'Redundancy, proactive monitoring, rapid response procedures'],
    ['Medium Risk', '7', 'Process controls, regular reviews, contingency planning'],
    ['Low Risk', '2', 'Standard procedures, monitoring, documentation'],
]

PRICING_INTRO = "The following commercial structure covers the services described in this proposal."

PRICING_SUMMARY_TABLE = [
    ['Service Component', 'Monthly Fee (INR)', 'Annual Fee (INR)', 'Notes'],
    ['Base Managed Service', '₹XXX', '₹XXXX', 'Includes all standard services'],
    ['24/7 SOC Monitoring & Support', 'Included', 'Included', 'Round-the-clock coverage'],
    ['Incident Response (P1-P4)', 'Included', 'Included', 'All severity levels'],
    ['Change Management', 'Included', 'Included', 'Up to 10 changes/month'],
    ['Health Monitoring', 'Included', 'Included', 'Proactive monitoring'],
    ['Patch Management', 'Included', 'Included', 'Security patches'],
    ['Firmware/OS Upgrades', 'Included', 'Included', 'Annual major upgrades'],
    ['Configuration Backup', 'Included', 'Included', 'Daily backups, 90-day retention'],
    ['Monthly Reporting', 'Included', 'Included', 'Standard reports'],
    ['Total Annual Investment', '₹XX/mo', '₹XXX', 'Annual commitment'],
]

OPTIONAL_PRICING_TABLE = [
    ['Service', 'Pricing Model', 'Notes'],
    ['On-Site Support', '₹X/day + expenses', 'When remote support is insufficient'],
    ['Emergency Changes (beyond scope)', '₹X/hour', 'Changes exceeding monthly limit'],
    ['Custom Reporting/Development', '₹X/hour', 'Non-standard reporting requirements'],
    ['Security Assessment/Audit', '₹XXX - ₹XXX', 'Based on scope and complexity'],
]

COMMERCIAL_TERMS = """Payment Terms

• Annual commitment with standard payment terms (Net 30)
• Invoicing monthly in arrears unless otherwise agreed
• Prices exclusive of applicable taxes and statutory levies

Service Term

• Initial term of 12 months from the service commencement date
• Renewal by mutual written agreement
• Termination for convenience with 90 days' written notice

Scope Changes

• Any expansion beyond the infrastructure scope defined in this proposal is subject to additional charges
• Professional services for migration projects are quoted separately
• Third-party costs (licenses, cloud resources) are not included unless specified"""

WHY_US_INTRO = """Choosing the right managed security partner is critical for protecting your organization's digital assets. 63SATS Cybertech Limited offers a unique combination of technical expertise, operational excellence, and customer-centric service that sets us apart from other MSSPs."""

TECHNOLOGY_EXPERTISE = """Our team holds advanced security certifications including Palo Alto, Check Point, Fortinet, Cisco and other security specialist credentials. We have deep expertise in deploying and managing security physical and virtual appliances across enterprise environments and centralized management at scale."""

CERTIFICATION_TABLE = [
    ['Certification', 'Relevance to Your Environment'],
    ['Firewall Security', 'Advanced routing, firewall, and VPN expertise'],
    ['CISSP', 'Comprehensive security management approach'],
    ['CISM', 'Security governance and risk management'],
]

TRACK_RECORD = """We have successfully managed security infrastructures for organizations across various industries, including financial services, healthcare, manufacturing, and technology. Our clients trust us with their most critical security infrastructure."""

TRACK_RECORD_TABLE = [
    ['Metric', 'Our Performance', 'Industry Average'],
    ['Infrastructure Uptime', '99.99%', '99.9%'],
    ['P1 Response Time', '< 15 minutes', '30-60 minutes'],
    ['Customer Satisfaction', '4.7/5', '4.0/5'],
    ['Change Success Rate', '99.2%', '95%'],
    ['Employee Retention', '92%', '75%'],
    ['Client Retention', '95%', '80%'],
]

CUSTOMER_CENTRIC = """We believe in building long-term partnerships with our clients. Our customer-centric approach ensures that your unique requirements are understood and addressed proactively.

• Dedicated Account Team: Single point of contact who knows your environment
• Tailored Reporting: Customized reports that matter to your stakeholders
• Proactive Communication: Regular updates and recommendations
• Flexible Engagement: Services that adapt to your changing needs
• Transparent Pricing: No hidden costs or surprise charges"""

PARTNERSHIP_ECOSYSTEM = """Our strong partnerships with leading technology vendors ensure you receive the best support and access to the latest innovations.

• OEM Partnerships: Direct access to vendor TAC and engineering teams
• Cloud Partnerships: Azure, AWS, and GCP expertise for cloud deployments
• Threat Intelligence Partners: Integration with leading threat intel providers
• Technology Alliances: Partnerships that enhance our service capabilities"""

OUR_COMMITMENT = """When you partner with 63SATS, you gain more than a service provider — you gain a dedicated security partner committed to your success. Our commitment to you includes:

• Service Excellence: Consistent, high-quality service delivery
• Transparency: Open communication and honest reporting
• Continuous Improvement: Ongoing enhancement of our services
• Security First: Your security is our top priority
• Long-term Partnership: Building relationships that last

We look forward to the opportunity to demonstrate why 63SATS is the right choice for your managed security needs."""

KEY_VALUE_PROPOSITIONS = """• Expert Management: Certified security professionals managing your infrastructure
• 24/7 Coverage: Round-the-clock monitoring with skilled analysts across time zones
• Proactive Approach: Health monitoring, threat intelligence, and preventive maintenance
• Structured Processes: Documented change management, patch management, and incident response
• Future-Ready: Optional migration services for infrastructure modernization
• Clear Accountability: Defined RACI matrix ensuring clarity of roles and responsibilities
• Risk Management: Comprehensive risk assessment and mitigation strategies"""

OUTCOMES_TABLE = [
    ['Outcome', 'Measurement', 'Target'],
    ['Infrastructure Availability', 'Uptime percentage across all managed devices', '99.99%'],
    ['Incident Response Time', 'Mean Time to Respond (MTTR) for P1 incidents', '< 15 minutes'],
    ['Change Success Rate', 'Percentage of changes completed without issues', '> 98%'],
    ['Patch Compliance', 'Percentage of critical patches applied within SLA', '100%'],
    ['Customer Satisfaction', 'Monthly satisfaction score', '> 4.5/5'],
    ['Security Posture', 'Number of security incidents per month', 'Zero critical incidents'],
]

NEXT_STEPS = """To proceed with this engagement, we propose the following next steps:

1. Schedule a technical deep-dive session to review infrastructure details and clarify any questions
2. Conduct a formal proposal presentation to key stakeholders and decision makers
3. Finalize service scope, SLA parameters, and any customization requirements
4. Negotiate and execute Master Service Agreement (MSA) and Statement of Work (SOW)
5. Initiate transition planning and establish project kick-off date"""

BUSINESS_TERMS = """Confidentiality

The contents of this proposal with all annexure(s) ("Proposal" / "Letter" / "Agreement") and or Purchase Order ("PO") and all the information including without limitation all correspondence ("Confidential Information") shared by 63SATS CYBERTECH LIMITED (formerly known as 63SATS Global Cyber Technologies Networks Limited) ("63SATS") with your organization ("Client") ["63SATS" and the "Client" are also referred to individually as "Party" and collectively as "Parties"] whether in oral, graphic, written or in any other form etc. should be strictly maintained confidential. Client shall not disclose such Confidential Information and the contents of the Proposal and either in parts or in full to any third party without prior written consent from 63SATS.

Intellectual Property

Where either Party has any intellectual property rights in any material that is subsequently used by the parties in connection with this Proposal, then those intellectual property rights remain vested in that Party originally holding the intellectual property rights.

The Client hereby agrees that 63SATS is entitled to make reference to the Client's name, brand and logo in the 63SATS's marketing materials and as part of its sales presentations to other potential customers or customers, notwithstanding the termination or expiry of this engagement.

Support

The Client acknowledges and understands that the performance of Services is contingent and dependent upon the fulfilment of certain prerequisites and actions by the Client. It will be responsibility of the Client to ensure and identify one suitably qualified person to co-ordinate the activities relating to the implementation of the scope and to manage day to day technical administration / operations.

Limitation of Liability

In no event shall 63SATS be liable to Client and any third party for and direct, indirect, loss of profits, data or use of the product or special incidental or consequential damages or other similar claims, however caused, and on any theory of liability.

Enforceability

This Proposal is not a contract, as the parties do not intend to create a legally binding agreement. The parties propose to negotiate in good faith, and within a reasonable time period and create definitive agreement(s) at a later date to incorporate the scope of products/services, roles and responsibilities, pricing, etc. Until such time as a definitive agreement(s) is/are executed between the parties, both parties propose to work closely together to identify potential opportunities.

Legal Disclaimer

The information provided herein is delivered on as-is basis and makes no representations, warranties, conditions or covenants of any kind, either express, implied, statutory, or otherwise, including any representations, conditions or warranties of merchantability or satisfactory quality, non-infringement title, durability, fitness for a particular purpose, or that will work uninterrupted or error-free. 63SATS shall not be responsible or liable for any business decision made in reliance on disclosures made pursuant to this proposed process and structure plan. 63SATS does not warrant or guarantee that it will achieve any performance, or results projected in the proposed process and structure plan and should not be read as a guarantee of future performance or results and may not be accurate indications of when such performance or results will be achieved. There can be no assurance that the actual results or developments anticipated by the company will be realized or, that they will have the expected consequences. Therefore, no assurance can be given that the outcomes stated, and estimates will be achieved. All written and verbal statements attributable to the company or any person acting on its behalf are expressly qualified in their entirety by the cautionary statements contained or referred to herein. The information in this proposed process and structure plan is provided only as of the date of this release, and 63SATS undertakes no obligation, and specifically declines any obligation, to update or revise any statements, whether as a result of new information, future events or otherwise."""


CONCLUSION = """In today's rapidly evolving threat landscape, organizations need a trusted partner to help them navigate cybersecurity challenges. 63SATS offers a comprehensive solution that addresses your security needs while enabling your team to focus on core business objectives.

We are confident that our proposed solution will deliver significant value to your organization, enhancing your security posture and providing peace of mind.

We look forward to the opportunity to partner with you and demonstrate our commitment to your success.

Thank you for considering 63SATS as your cybersecurity partner."""


def generate_proposal_document(
    template_content: Optional[str],
    extracted_data: Dict,
    output_filename: str = "proposal.docx"
) -> bytes:
    """
    Generate a Word document following the 63SATS proposal format.
    """
    doc = Document()

    # Page setup, style set, header and footer are configured before any
    # content is written so every page shares the same furniture.
    _configure_page(doc)
    _configure_styles(doc)
    _pin_default_font(doc)
    _enable_field_update(doc)

    client_name = extracted_data.get('client_name') or '[Client Name]'
    subtitle = extracted_data.get('project_title') or 'Cybersecurity Services Proposal'

    nums = _Numbering()

    _configure_header_footer(doc)
    _add_cover_page(doc, extracted_data, client_name, subtitle)

    # Document Control — attribute/details table, as in the template
    _add_heading(doc, 'Document Control', 1)
    _add_table(doc, [
        ['Attribute', 'Details'],
        ['Document Title', subtitle],
        ['Version', str(extracted_data.get('version', '0.0'))],
        ['Date', extracted_data.get('date', '23rd May 2026')],
        ['Prepared By', extracted_data.get('submitted_by', '63SATS Team')],
        ['Classification', extracted_data.get(
            'classification', 'Confidential - Client Use Only')],
        ['Status', extracted_data.get('status', 'Draft for Review')],
    ], header=True, widths=[2.2, 4.2])

    _add_heading(doc, 'Disclaimer of Copyrights', 1, page_break=True)
    _add_body_text(doc, DOCUMENT_CONTROL)

    _add_toc(doc)

    # ============================================
    # EXECUTIVE SUMMARY
    # ============================================
    # Written against the actual RFP by services/proposal_writer; the fallback
    # exists only so a proposal with no RFP text still renders.
    _section(doc, nums, 'Executive Summary')
    exec_summary = extracted_data.get('executive_summary') or f"""63SATS is pleased to submit this proposal to {client_name} for {subtitle}.

This document sets out our understanding of your requirements, the solution we propose, our implementation approach, the commercial structure, and the value 63SATS brings to this engagement."""
    _add_body_text(doc, exec_summary)

    # ============================================
    # SECTION 1: INTRODUCTION
    # ============================================
    _section(doc, nums, 'Introduction')

    _subsection(doc, nums, 'About 63SATS')
    _add_body_text(doc, ABOUT_63SATS)

    _subsection(doc, nums, 'Proposal Overview')
    project_title = subtitle
    overview = extracted_data.get('proposal_overview', f"""63SATS is pleased to present this proposal for {project_title} for {client_name}.

{extracted_data.get('current_environment', 'The proposal outlines our understanding of your requirements, proposed solution, implementation approach, and the value we bring to your organization.')}""")
    _add_body_text(doc, overview)

    # ============================================
    # UNDERSTANDING OF CLIENT REQUIREMENTS
    # ============================================
    # The section evaluation committees weight most heavily, and the one the
    # legacy boilerplate had no answer for at all.
    understanding = extracted_data.get('understanding_of_requirements')
    traceability = extracted_data.get('requirements_traceability')
    if understanding or traceability:
        _section(doc, nums, 'Understanding of Client Requirements')
        if understanding:
            _add_body_text(doc, understanding)
        if traceability:
            _subsection(doc, nums, 'Requirement Compliance Matrix')
            _add_body_text(doc, traceability)

    # ============================================
    # SECTION 2: CURRENT ENVIRONMENT SUMMARY
    # ============================================
    _section(doc, nums, 'Current Environment Summary')
    current_env_default = '''The current environment summary provides context for the proposed solution. This section describes the existing infrastructure, challenges, and requirements that form the basis of our proposal.'''
    current_env = extracted_data.get('current_environment', extracted_data.get('current_challenges', current_env_default))
    _add_body_text(doc, current_env)

    # ============================================
    # SECTION 3: OBJECTIVES
    # ============================================
    _section(doc, nums, 'Objectives')
    objectives_default = '''The primary objectives of this engagement are:

1. Enhance organizational security posture through comprehensive monitoring and protection
2. Achieve and maintain compliance with relevant regulatory frameworks
3. Reduce mean time to detect (MTTD) and mean time to respond (MTTR) to security incidents
4. Gain complete visibility into endpoints, networks, and cloud environments
5. Enable proactive threat hunting and intelligence-led security operations
6. Build internal security awareness and capabilities through knowledge transfer
7. Establish incident response procedures and playbooks
8. Provide transparent reporting and metrics demonstrating security improvements'''
    objectives = extracted_data.get('objectives', objectives_default)
    _add_body_text(doc, objectives)

    # ============================================
    # SECTION 4: SCOPE OF WORK
    # ============================================
    _section(doc, nums, 'Scope of Work')

    _subsection(doc, nums, 'Assessment & Design')
    assessment_default = '''• Review existing network architecture
• Identify key placement points
• Define security zones and conduits
• Design solution architecture aligned with best practices'''
    assessment = extracted_data.get('assessment', assessment_default)
    _add_body_text(doc, assessment)

    _subsection(doc, nums, 'Implementation')
    implementation_default = '''• Deploy solution components as per design
• Configure policies and settings
• Integrate with existing systems
• Establish monitoring and alerting'''
    implementation = extracted_data.get('implementation', implementation_default)
    _add_body_text(doc, implementation)

    _subsection(doc, nums, 'Key Services to be Delivered')
    services_default = '''
• Platform deployment and configuration
• 24/7 security operations monitoring
• Incident response and threat hunting
• Compliance management and reporting
• Change management
• Patch and firmware management
• Health monitoring
• Weekly and monthly reporting'''
    services = extracted_data.get('key_services') or extracted_data.get('scope_of_work') or services_default
    _add_body_text(doc, services)

    # ============================================
    # SECTION 5: SOLUTION PROPOSED
    # ============================================
    _section(doc, nums, 'Solution Proposed')
    solution_default = '''63SATS proposes a comprehensive cybersecurity solution combining industry-leading security technology with our expert managed security services.

Key Components:

1. Security Platform
   • AI-powered protection
   • Real-time threat intelligence
   • Cloud-native architecture
   • Unified visibility across all environments

2. 63SATS Managed Services
   • Expert security analysts monitoring 24/7/365
   • Proactive threat hunting
   • Incident response coordination
   • Compliance reporting and support

3. Integration & Automation
   • Seamless integration with existing tools
   • Automated response workflows
   • Custom detection rules tailored to your environment
   • SOAR playbook development and implementation'''
    technical_solution = extracted_data.get('technical_solution')
    solution = extracted_data.get('solution_proposed')

    if technical_solution:
        # The engineered design for this specific RFP (architecture, HA, VPN,
        # policy, sizing, licensing). Where it exists it is the substance of
        # this section and the generic overview is redundant.
        if solution:
            _subsection(doc, nums, 'Solution Overview')
            _add_body_text(doc, solution)
            _subsection(doc, nums, 'Technical Solution Design')
        _add_body_text(doc, technical_solution)
    else:
        _add_body_text(doc, solution or solution_default)

    bom = extracted_data.get('bill_of_materials')
    if bom:
        _subsection(doc, nums, 'Bill of Materials')
        _add_body_text(doc, bom)

    # ============================================
    # SECTION 6: IMPLEMENTATION PLAN
    # ============================================
    _section(doc, nums, 'Implementation Plan')

    _subsection(doc, nums, 'Implementation Approach')
    approach_default = '''Our implementation follows a structured, phased approach designed to minimize disruption and ensure successful deployment:

Phase 1: Discovery and Planning
• Assess current environment and inventory all assets
• Define success criteria and key performance indicators
• Develop detailed project timeline and resource plan
• Identify stakeholders and communication requirements

Phase 2: Implementation
• Deploy solution components (staged rollout)
• Configure policies and protection settings
• Integrate with existing systems
• Establish data feeds and alerting channels

Phase 3: Optimization
• Fine-tune detection rules and alerting thresholds
• Configure baseline behaviors for your environment
• Develop custom detection use cases
• Create runbooks and playbooks

Phase 4: Operational Handoff
• Train client team on platform usage and reporting
• Document procedures and operational runbooks
• Establish communication protocols and escalation paths
• Transition to steady-state operations'''
    approach = extracted_data.get('implementation_approach', approach_default)
    _add_body_text(doc, approach)

    _subsection(doc, nums, 'Implementation Methodology')
    methodology_default = '''63SATS follows industry-standard implementation methodologies:

• Agile Project Management: Iterative approach with regular checkpoints and flexibility for scope adjustments
• ITIL-aligned Service Management: Best practices for service delivery and incident management
• Industry Best Practices: Proven deployment methodologies refined through numerous implementations
• Collaborative Approach: Regular communication with stakeholder feedback at each milestone

Project Governance:
• Weekly status meetings with project team
• Bi-weekly steering committee updates
• Documented change management process
• Risk and issue tracking with mitigation plans
• Quality assurance checkpoints'''
    methodology = extracted_data.get('implementation_methodology', methodology_default)
    _add_body_text(doc, methodology)

    # ============================================
    # TRANSITION APPROACH & TIMELINE
    # ============================================
    _section(doc, nums, 'Transition Approach & Timeline')
    _add_body_text(doc, extracted_data.get('transition_approach',
                                           TRANSITION_APPROACH))

    _subsection(doc, nums, 'Transition Timeline Summary')
    _add_table(doc, TRANSITION_TIMELINE_TABLE, header=True,
               widths=[1.6, 1.6, 3.2])

    # ============================================
    # OPERATIONAL ACTIVITIES
    # ============================================
    _section(doc, nums, 'Operational Activities')
    _add_body_text(doc, OPERATIONAL_ACTIVITIES_INTRO)

    _subsection(doc, nums, 'Daily Operations')
    _add_body_text(doc, extracted_data.get('daily_operations', DAILY_OPERATIONS))

    _subsection(doc, nums, 'Weekly Activities')
    _add_body_text(doc, extracted_data.get('weekly_activities', WEEKLY_ACTIVITIES))

    _subsection(doc, nums, 'Monthly Activities')
    _add_body_text(doc, extracted_data.get('monthly_activities', MONTHLY_ACTIVITIES))

    _subsection(doc, nums, 'Quarterly Activities')
    _add_body_text(doc, extracted_data.get('quarterly_activities',
                                           QUARTERLY_ACTIVITIES))

    # ============================================
    # OPTIONAL ONE-TIME MIGRATION SERVICES
    # ============================================
    _section(doc, nums, 'Optional One-Time Migration Services')
    _add_body_text(doc, extracted_data.get('optional_migration',
                                           OPTIONAL_MIGRATION))

    # ============================================
    # SECTION 7: RACI MATRIX
    # ============================================
    _section(doc, nums, 'RACI Matrix')

    raci_intro = '''The following RACI (Responsible, Accountable, Consulted, Informed) matrix defines the roles and responsibilities between 63SATS (MSSP) and the Client for key activities in the engagement.'''
    _add_body_text(doc, raci_intro)

    # An engagement-specific matrix is rendered from its markdown table; the
    # fixed table below is the fallback for proposals with no RFP text.
    raci_matrix = extracted_data.get('raci_matrix')
    if raci_matrix:
        _add_body_text(doc, raci_matrix)
        _add_paragraph(
            doc,
            "R = Responsible (Does the work) | A = Accountable (Final decision maker) | "
            "C = Consulted (Provides input) | I = Informed (Notified of outcomes)",
            size=Pt(9), italic=True, color=MUTED_COLOR)
        raci_data = None
    else:
        raci_data = [
            ['Activity', '63SATS', 'Client'],
            ['Discovery & Assessment', 'R', 'A'],
            ['Solution Design', 'R', 'A'],
            ['Implementation', 'R', 'A'],
            ['Configuration', 'R', 'A'],
            ['Testing & Validation', 'R', 'A'],
            ['User Training', 'R', 'A'],
            ['24/7 Monitoring', 'R', 'I'],
            ['Incident Response', 'R', 'A'],
            ['Change Management', 'R', 'A'],
            ['Weekly Reporting', 'R', 'I'],
            ['Monthly Review', 'R', 'A'],
            ['Patch Management', 'R', 'A'],
        ]

        _add_table(doc, raci_data, header=True, widths=[3.5, 1.5, 1.5])

        _add_paragraph(
            doc,
            "R = Responsible (Does the work) | A = Accountable (Final decision maker) | "
            "C = Consulted (Provides input) | I = Informed (Notified of outcomes)",
            size=Pt(9), italic=True, color=MUTED_COLOR)

    # ============================================
    # SECTION 8: ASSUMPTIONS
    # ============================================
    _section(doc, nums, 'Assumptions')
    assumptions_default = '''This proposal is based on the following assumptions. Any changes to these assumptions may impact scope, timeline, and commercial terms.

Infrastructure Assumptions

• All systems are operational and accessible for implementation
• Network connectivity is available for all monitored assets
• Sufficient admin access will be provided for implementation
• Required firewall ports will be opened

Access & Connectivity Assumptions

• 63SATS will be provided with secure VPN access to the client network
• Administrative access will be provisioned for 63SATS team
• Email and ticketing system integration will be established

Process Assumptions

• Client will designate primary and secondary points of contact for approvals
• Change approval workflows will be defined within 2 weeks of engagement start
• Maintenance windows will be agreed upon and scheduled in advance
• Client will provide timely responses to approval requests (within 24-48 hours)

Commercial Assumptions

• Pricing is based on the scope defined in this proposal
• Pricing assumes annual commitment with standard payment terms
• Any scope expansion will be subject to additional charges
• Professional services are quoted separately'''
    assumptions = extracted_data.get('assumptions') or assumptions_default
    _add_body_text(doc, assumptions)

    # ============================================
    # SECTION 9: DEPENDENCIES
    # ============================================
    _section(doc, nums, 'Dependencies')
    _add_body_text(doc, extracted_data.get(
        'dependencies',
        'Successful delivery of services is dependent on the following '
        'factors. Timely resolution of dependencies is critical for '
        'maintaining service quality and meeting agreed service levels.'))

    _subsection(doc, nums, 'Client Dependencies')
    _add_table(doc, CLIENT_DEPENDENCIES_TABLE, header=True,
               widths=[2.1, 2.2, 2.1])

    _subsection(doc, nums, '63SATS Dependencies')
    _add_table(doc, SATS_DEPENDENCIES_TABLE, header=True,
               widths=[2.1, 2.2, 2.1])

    _subsection(doc, nums, 'External Dependencies')
    _add_table(doc, EXTERNAL_DEPENDENCIES_TABLE, header=True,
               widths=[2.0, 2.9, 1.5])

    _subsection(doc, nums, 'Critical Path Dependencies')
    _add_body_text(doc, CRITICAL_PATH_DEPENDENCIES)

    # ============================================
    # SECTION 10: IMPLEMENTATION TIMELINE
    # ============================================
    _section(doc, nums, 'Implementation Timeline')
    timeline_default = '''The proposed implementation timeline is as follows:

Week 1-2: Discovery and Planning
• Environment assessment and asset inventory
• Requirements gathering and validation
• Project kickoff meeting

Week 3-4: Implementation
• Component deployment (staged rollout)
• Policy configuration and initial tuning
• Basic integrations and monitoring setup

Week 5-6: Optimization
• Fine-tuning and customization
• User training sessions
• Runbook and playbook development

Week 7-8: Operations Handoff
• Go-live preparation
• Operational transition
• Final training and documentation

Total Implementation: 6-8 weeks'''
    timeline = extracted_data.get('timeline') or extracted_data.get('implementation_timeline') or timeline_default
    _add_body_text(doc, timeline)

    # ============================================
    # SECTION 11: EXPECTED OUTCOMES
    # ============================================
    _section(doc, nums, 'Expected Outcomes and ROI')
    roi_default = '''Through this engagement, the client can expect to achieve:

1. Security Improvements
   • 60% reduction in mean time to detect (MTTD)
   • 70% improvement in incident response times
   • 95% visibility across all assets
   • Proactive threat identification before data breach occurs

2. Operational Benefits
   • 24/7/365 security monitoring without internal headcount
   • Access to enterprise-grade security technology
   • Centralized security visibility across all environments
   • Automated response capabilities

3. Compliance Support
   • Continuous compliance monitoring and reporting
   • Audit-ready evidence collection
   • Policy enforcement and documentation

4. Financial Impact
   • Reduced security incidents and associated costs
   • Predictable security spend (OpEx vs CapEx)
   • Avoided costs of building and maintaining in-house SOC'''
    roi = extracted_data.get('expected_outcomes') or extracted_data.get('roi') or roi_default
    _add_body_text(doc, roi)

    # ============================================
    # RISK & MITIGATIONS
    # ============================================
    _section(doc, nums, 'Risk & Mitigations')
    risk_content = extracted_data.get('risk_mitigations')
    _add_body_text(doc, risk_content or RISK_TEMPLATE)

    # The heat map's counts describe the generic register above it; suppress it
    # when an engagement-specific register has replaced that register, rather
    # than publishing a summary that contradicts the table it summarises.
    if not risk_content:
        _subsection(doc, nums, 'Risk Heat Map Summary')
        _add_table(doc, RISK_HEAT_MAP_TABLE, header=True, widths=[1.5, 0.9, 4.0])

    # ============================================
    # CONCLUSION
    # ============================================
    _section(doc, nums, 'Conclusion')
    conclusion_text = extracted_data.get('conclusion') or CONCLUSION.replace(
        "your organization", client_name)
    _add_body_text(doc, conclusion_text)

    _subsection(doc, nums, 'Key Value Propositions')
    _add_body_text(doc, KEY_VALUE_PROPOSITIONS)

    _subsection(doc, nums, 'Expected Outcomes')
    _add_table(doc, OUTCOMES_TABLE, header=True, widths=[2.1, 2.9, 1.4])

    _subsection(doc, nums, 'Next Steps')
    _add_body_text(doc, NEXT_STEPS)

    # ============================================
    # COMMERCIAL WITH TERMS & CONDITIONS
    # ============================================
    _section(doc, nums, 'Commercial with Terms & Conditions')

    _subsection(doc, nums, 'Pricing Summary')
    _add_body_text(doc, extracted_data.get('pricing_information', PRICING_INTRO))
    _add_table(doc, PRICING_SUMMARY_TABLE, header=True,
               widths=[2.4, 1.3, 1.3, 1.4])

    _subsection(doc, nums, 'Optional Services Pricing')
    _add_table(doc, OPTIONAL_PRICING_TABLE, header=True, widths=[2.4, 1.8, 2.2])

    _subsection(doc, nums, 'Terms & Conditions')
    _add_body_text(doc, extracted_data.get('terms_and_conditions',
                                           COMMERCIAL_TERMS))

    # ============================================
    # WHY 63SATS
    # ============================================
    _section(doc, nums, 'Why 63SATS')
    _add_body_text(doc, extracted_data.get('why_63sats') or WHY_US_INTRO)

    _subsection(doc, nums, 'Technology Expertise')
    _add_body_text(doc, TECHNOLOGY_EXPERTISE)
    _add_table(doc, CERTIFICATION_TABLE, header=True, widths=[2.2, 4.2])

    _subsection(doc, nums, 'Proven Track Record')
    _add_body_text(doc, TRACK_RECORD)
    _add_table(doc, TRACK_RECORD_TABLE, header=True, widths=[2.4, 2.0, 2.0])

    _subsection(doc, nums, 'Customer-Centric Approach')
    _add_body_text(doc, CUSTOMER_CENTRIC)

    _subsection(doc, nums, 'Partnership Ecosystem')
    _add_body_text(doc, PARTNERSHIP_ECOSYSTEM)

    _subsection(doc, nums, 'Our Commitment')
    _add_body_text(doc, OUR_COMMITMENT)

    # ============================================
    # BUSINESS TERMS AND CONDITIONS
    # ============================================
    _section(doc, nums, 'Business Terms and Conditions')
    _add_body_text(doc, BUSINESS_TERMS)

    _add_paragraph(doc, space_after=Pt(12))
    _add_table(doc, [
        ['', f'Signed for and on behalf of {client_name}'],
        ['', ''],
        ['', 'Authorized Signatory (Please attach the Company Seal)'],
    ], header=False, widths=[3.2, 3.2])

    # Closing block
    closing = _add_paragraph(doc, space_after=Pt(0))
    closing.paragraph_format.space_before = Pt(24)
    _add_bottom_border(closing)

    _add_paragraph(doc, f'PROPOSAL PREPARED BY {COMPANY_NAME}', bold=True,
                   color=BRAND_COLOR, align=WD_ALIGN_PARAGRAPH.CENTER,
                   space_after=Pt(2))
    _add_paragraph(doc, CONFIDENTIALITY_NOTICE, size=Pt(9), italic=True,
                   color=MUTED_COLOR, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def apply_template_with_placeholders(template_content: str, extracted_data: Dict) -> str:
    """Replace {{placeholder}} tags in template with actual values."""
    result = template_content

    for key, value in extracted_data.items():
        placeholder = f"{{{{{key}}}}}"
        if value:
            result = result.replace(placeholder, str(value))
        else:
            result = result.replace(placeholder, '[Not Provided]')

    return result


def create_template_from_content(content: str) -> str:
    """Create a template document from Word content."""
    doc = Document(io.BytesIO(content))
    text_content = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_content.append(para.text)

    return '\n\n'.join(text_content)


def extract_placeholders_from_template(content: str) -> list:
    """Extract all {{placeholder}} patterns from template content."""
    pattern = r'\{\{([^}]+)\}\}'
    return re.findall(pattern, content)