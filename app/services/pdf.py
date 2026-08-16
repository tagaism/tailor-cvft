from __future__ import annotations

from io import BytesIO

from fpdf import FPDF

from app.cv_layout import contact_bits, role_dates, skill_lines
from app.richtext import rich_tokens
from app.schemas import Profile


class ResumePDF(FPDF):
    def footer(self) -> None:
        return


def html_to_pdf(
    html: str,
    *,
    cv: Profile | None = None,
    letter: str = "",
    job_title: str = "",
    company: str = "",
) -> bytes:
    if letter:
        return letter_to_pdf(cv or Profile(), letter, job_title, company)
    if cv is None:
        raise ValueError("A structured CV is required to build a PDF.")
    return cv_to_pdf(cv)


def _safe(text: str) -> str:
    cleaned = text or ""
    for src, dst in {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00b7": "-",
        "\u00a0": " ",
    }.items():
        cleaned = cleaned.replace(src, dst)
    return cleaned.encode("latin-1", "replace").decode("latin-1")


def _usable_width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _write(
    pdf: FPDF,
    text: str,
    *,
    width: float | None = None,
    height: float = 5,
    font: str = "Times",
    style: str = "",
    size: float = 11,
    align: str = "L",
    indent: float = 0,
) -> None:
    pdf.set_font(font, style, size)
    pdf.set_x(pdf.l_margin + indent)
    usable = _usable_width(pdf) - indent
    line_width = usable if width is None else width
    pdf.multi_cell(
        line_width,
        height,
        _safe(text),
        align=align,
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _write_rich(pdf: FPDF, html_text: str, *, indent: float = 0, prefix: str = "-  ") -> None:
    pdf.set_x(pdf.l_margin + indent)
    pdf.set_font("Times", "", 11)
    if prefix:
        pdf.write(5, prefix)
    tokens = rich_tokens(html_text)
    if not tokens:
        pdf.write(5, _safe(html_text))
    else:
        for style, text in tokens:
            pdf.set_font("Times", style, 11)
            pdf.write(5, _safe(text))
    pdf.ln(5)
    pdf.set_x(pdf.l_margin)


def _split_row(pdf: FPDF, left_top: str, left_bottom: str, right_top: str, right_bottom: str) -> None:
    epw = _usable_width(pdf)
    left_w = epw * 0.64
    right_w = epw - left_w
    x0 = pdf.l_margin
    y0 = pdf.get_y()

    pdf.set_xy(x0, y0)
    pdf.set_font("Times", "B", 11)
    pdf.multi_cell(left_w, 5, _safe((left_top or "").upper()), new_x="LMARGIN", new_y="NEXT")
    y_company = pdf.get_y()
    pdf.set_xy(x0, y_company)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(left_w, 5, _safe(left_bottom or ""), new_x="LMARGIN", new_y="NEXT")
    y_left = pdf.get_y()

    pdf.set_xy(x0 + left_w, y0)
    pdf.set_font("Times", "B", 11)
    pdf.multi_cell(right_w, 5, _safe(right_top or ""), align="R", new_x="LMARGIN", new_y="NEXT")
    y_loc = pdf.get_y()
    pdf.set_xy(x0 + left_w, y_loc)
    pdf.set_font("Times", "I", 11)
    pdf.multi_cell(right_w, 5, _safe(right_bottom or ""), align="R", new_x="LMARGIN", new_y="NEXT")
    y_right = pdf.get_y()

    pdf.set_xy(x0, max(y_left, y_right) + 0.4)


def cv_to_pdf(cv: Profile) -> bytes:
    pdf = ResumePDF(format="Letter")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    epw = _usable_width(pdf)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.35)

    _write(pdf, cv.contact.full_name or "Resume", height=8, style="B", size=20, align="C")
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y + 0.6, pdf.l_margin + epw, y + 0.6)
    pdf.set_y(y + 2.2)
    bits = contact_bits(cv)
    if bits:
        _write(pdf, " | ".join(bits), height=5, size=10, align="C")

    if cv.summary:
        pdf.ln(1.6)
        _write(pdf, cv.summary, height=5, size=11)

    def heading(title: str) -> None:
        pdf.ln(2.2)
        _write(pdf, title.upper(), height=6, style="B", size=12)
        y_line = pdf.get_y()
        pdf.line(pdf.l_margin, y_line, pdf.l_margin + epw, y_line)
        pdf.set_y(y_line + 1.6)

    lines = skill_lines(cv)
    if lines:
        heading("Technical Skills")
        for line in cv.skills or lines:
            _write_rich(pdf, line, indent=4)

    if cv.experience:
        heading("Professional Experience")
        for role in cv.experience:
            _split_row(pdf, role.company, role.title, role.location, role_dates(role))
            for bullet in role.bullets:
                _write_rich(pdf, bullet, indent=6)
            pdf.ln(1.4)

    if cv.projects:
        heading("Projects")
        for project in cv.projects:
            _split_row(pdf, project.name, project.description, "", project.url)
            for bullet in project.bullets:
                _write_rich(pdf, bullet, indent=6)
            pdf.ln(1)

    if cv.education:
        heading("Education")
        for edu in cv.education:
            degree = " in ".join(part for part in [edu.degree, edu.field] if part)
            if edu.details:
                degree = f"{degree}, {edu.details}" if degree else edu.details
            _split_row(pdf, edu.school, degree, edu.location, edu.end or edu.start)

    if cv.certifications:
        heading("Certifications")
        for cert in cv.certifications:
            parts = [cert.name, cert.issuer, f"({cert.year})" if cert.year else ""]
            _write(pdf, " - ".join(part for part in parts if part))

    if cv.additional_skills:
        heading("Additional Skills")
        for item in cv.additional_skills:
            _write_rich(pdf, item, indent=4)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def letter_to_pdf(cv: Profile, letter: str, job_title: str = "", company: str = "") -> bytes:
    pdf = ResumePDF(format="Letter")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _write(pdf, cv.contact.full_name or "", height=7, style="B", size=14)
    bits = [cv.contact.email, cv.contact.phone, cv.contact.location]
    _write(pdf, " | ".join(bit for bit in bits if bit), height=5, size=10)
    if job_title or company:
        _write(pdf, " | ".join(part for part in [job_title, company] if part), height=5, size=10)
    pdf.ln(6)
    for para in (letter or "").split("\n\n"):
        text = para.strip()
        if not text:
            continue
        _write(pdf, text, height=6)
        pdf.ln(2.5)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
