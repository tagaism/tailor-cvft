from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from app.config import APP_DIR
from app.cv_layout import contact_bits, role_dates, skill_lines
from app.richtext import letter_html, rich_tokens
from app.schemas import Profile, ShokumuCv


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


def _write_rich(
    pdf: FPDF,
    html_text: str,
    *,
    indent: float = 0,
    prefix: str = "-  ",
    height: float = 5,
    size: float = 11,
    br_extra: float = 0,
) -> None:
    pdf.set_x(pdf.l_margin + indent)
    pdf.set_font("Times", "", size)
    if prefix:
        pdf.write(height, prefix)
    tokens = rich_tokens(html_text)
    if not tokens:
        pdf.write(height, _safe(re.sub(r"<[^>]+>", "", html_text or "")))
    else:
        for style, text in tokens:
            if style == "br":
                pdf.ln(height + br_extra)
                pdf.set_x(pdf.l_margin + indent)
                continue
            pdf.set_font("Times", style, size)
            pdf.write(height, _safe(text))
    pdf.ln(height)
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
        _write_rich(pdf, cv.summary, prefix="")

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


def letter_to_pdf(
    cv: Profile,
    letter: str,
    job_title: str = "",
    company: str = "",
    *,
    japanese: bool = False,
    sender_name: str = "",
) -> bytes:
    if japanese:
        return _japanese_letter_pdf(cv, letter, job_title, company, sender_name)
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
    _write_rich(pdf, letter_html(letter), prefix="", height=6, size=12, br_extra=2.5)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


_JP_FONT = APP_DIR / "fonts" / "NotoSansJP-Regular.ttf"


def _ensure_jp_font() -> Path:
    if not _JP_FONT.exists():
        raise FileNotFoundError(
            f"Japanese PDF font missing: {_JP_FONT}. "
            "Keep app/fonts/NotoSansJP-Regular.ttf in the repo."
        )
    return _JP_FONT


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()


def _bind_jp(pdf: FPDF) -> None:
    font = _ensure_jp_font()
    pdf.add_font("JP", "", str(font))
    pdf.add_font("JP", "B", str(font))
    pdf.add_font("JP", "I", str(font))


def _write_jp(
    pdf: FPDF,
    text: str,
    *,
    style: str = "",
    size: float = 11,
    height: float = 5.5,
    indent: float = 0,
    align: str = "L",
) -> None:
    pdf.set_font("JP", style, size)
    pdf.set_x(pdf.l_margin + indent)
    width = pdf.w - pdf.l_margin - pdf.r_margin - indent
    pdf.multi_cell(width, height, text or "", align=align, new_x="LMARGIN", new_y="NEXT")


def _span(start: str, end: str) -> str:
    if start and end:
        return f"{start}〜{end}"
    return start or end or ""


def shokumu_to_pdf(cv: ShokumuCv) -> bytes:
    pdf = ResumePDF(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(auto=True, margin=14)
    _bind_jp(pdf)
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    _write_jp(pdf, "職　務　経　歴　書", style="B", size=16, height=8, align="C")
    if cv.as_of:
        _write_jp(pdf, cv.as_of, size=9, height=5, align="R")
    _write_jp(pdf, f"氏名　{cv.name}" if cv.name else "", style="B", size=12, height=7)
    pdf.ln(2)
    if cv.summary:
        _write_jp(pdf, "【職務要約】", style="B", size=12, height=7)
        _write_jp(pdf, _plain(cv.summary), size=10, height=5.2)
        pdf.ln(1.5)
    if cv.employers:
        _write_jp(pdf, "【職務経歴】", style="B", size=12, height=7)
        for employer in cv.employers:
            span = _span(employer.start, employer.end or "現在")
            _write_jp(pdf, f"{span}　　{employer.company}", style="B", size=10, height=5.5)
            line = "　".join(part for part in [employer.business and f"事業内容：{employer.business}", employer.employment_type] if part)
            if line:
                _write_jp(pdf, line, size=10, height=5)
            facts = [
                employer.capital and f"資本金：{employer.capital}",
                employer.revenue and f"売上高：{employer.revenue}",
                employer.employees and f"従業員数：{employer.employees}",
                employer.listing and f"上場：{employer.listing}",
            ]
            fact_line = "　".join(part for part in facts if part)
            if fact_line:
                _write_jp(pdf, fact_line, size=9, height=5)
            for item in employer.assignments:
                _write_jp(pdf, _span(item.start, item.end or "現在"), style="B", size=10, height=5)
                if item.department:
                    _write_jp(pdf, item.department, size=10, height=5)
                if item.duties:
                    _write_jp(pdf, "【職務内容】", style="B", size=10, height=5)
                    _write_jp(pdf, _plain(item.duties), size=10, height=5.2, indent=3)
                if item.points:
                    _write_jp(pdf, "【ポイント】", style="B", size=10, height=5)
                    _write_jp(pdf, _plain(item.points), size=10, height=5.2, indent=3)
            pdf.ln(1.4)
    if cv.pc_skills:
        _write_jp(pdf, "【PCスキル】", style="B", size=12, height=7)
        for skill in cv.pc_skills:
            if not skill.name:
                continue
            line = skill.name if not skill.level else f"{skill.name}　{skill.level}"
            _write_jp(pdf, line, size=10, height=5.2)
        pdf.ln(1.2)
    if cv.certifications:
        _write_jp(pdf, "【資格】", style="B", size=12, height=7)
        for cert in cv.certifications:
            if not cert.name:
                continue
            line = cert.name if not cert.date else f"{cert.name}　{cert.date}取得"
            _write_jp(pdf, line, size=10, height=5.2)
        pdf.ln(1.2)
    if cv.self_pr:
        _write_jp(pdf, "【自己ＰＲ】", style="B", size=12, height=7)
        _write_jp(pdf, _plain(cv.self_pr), size=10, height=5.2)
        pdf.ln(2)
    _write_jp(pdf, "以上", size=10, height=6, align="R")
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def _japanese_letter_pdf(
    cv: Profile,
    letter: str,
    job_title: str,
    company: str,
    sender_name: str,
) -> bytes:
    pdf = ResumePDF(format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    _bind_jp(pdf)
    pdf.add_page()
    name = sender_name or cv.contact.full_name
    _write_jp(pdf, name, style="B", size=13, height=7)
    bits = [cv.contact.email, cv.contact.phone, cv.contact.location]
    line = " · ".join(bit for bit in bits if bit)
    if line:
        _write_jp(pdf, line, size=9, height=5)
    if job_title or company:
        _write_jp(pdf, " · ".join(part for part in [job_title, company] if part), size=9, height=5)
    pdf.ln(4)
    _write_jp(pdf, "志望動機", style="B", size=12, height=7)
    _write_jp(pdf, _plain(letter_html(letter)), size=11, height=6)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
