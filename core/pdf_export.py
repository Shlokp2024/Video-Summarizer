import re
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

_styles = getSampleStyleSheet()
_body = ParagraphStyle("body", parent=_styles["BodyText"], fontSize=11, leading=15, spaceAfter=4)
_h1 = ParagraphStyle("h1", parent=_styles["Title"], fontSize=20, spaceAfter=6)
_h2 = ParagraphStyle("h2", parent=_styles["Heading2"], spaceBefore=10, spaceAfter=4)
_meta = ParagraphStyle("meta", parent=_body, textColor="#666666", fontSize=9)


def _inline(text: str) -> str:
    text = escape(text.replace("`", ""))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def _bullet_style(level: int) -> ParagraphStyle:
    return ParagraphStyle(
        f"b{level}", parent=_body,
        leftIndent=16 + level * 16, bulletIndent=4 + level * 16,
    )


def summary_to_pdf(title: str, summary: str, source: str = "") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=title,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )

    story = [Paragraph(_inline(title), _h1)]
    meta = datetime.now().strftime("Generated on %d %B %Y")
    if source:
        meta += f" · Source: {escape(source)}"
    story += [Paragraph(meta, _meta), Spacer(1, 12)]

    for line in summary.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            story.append(Paragraph(_inline(line.lstrip("# ").strip()), _h2))
            continue
        m = re.match(r"^(\s*)[-*•]\s+(.*)", line)
        if m:
            level = min(len(m.group(1)) // 2, 3)
            story.append(Paragraph(_inline(m.group(2)), _bullet_style(level), bulletText="•"))
        else:
            story.append(Paragraph(_inline(line.strip()), _body))

    doc.build(story)
    return buf.getvalue()