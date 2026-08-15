from __future__ import annotations

from io import BytesIO

from fpdf import FPDF

from app.schemas import Profile


class ResumePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 113, 108)
        self.cell(0, 8, str(self.page_no()), align="C")


def html_to_pdf(
    html: str,
    *,
    cv: Profile | None = None,
    letter: str = "",
    job_title: str = "",
    company: str = "",
) -> bytes:
    # html is kept so preview and PDF stay on the same route contract.
    if letter:
        return letter_to_pdf(cv or Profile(), letter, job_title, company)
    if cv is None:
        raise ValueError("A structured CV is required to build a PDF.")
    return cv_to_pdf(cv)


def _safe(text: str) -> str:
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def _usable_width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _row(pdf: FPDF, left: str, right: str, *, bold_left: bool = True) -> None:
    epw = _usable_width(pdf)
    left_w = epw * 0.68
    right_w = epw - left_w
    y = pdf.get_y()
    pdf.set_xy(pdf.l_margin, y)
    pdf.set_font("Helvetica", "B" if bold_left else "", 10)
    pdf.set_text_color(28, 25, 23)
    pdf.multi_cell(left_w, 5, _safe(left), new_x="RIGHT", new_y="TOP")
    left_bottom = pdf.get_y()
    pdf.set_xy(pdf.l_margin + left_w, y)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(87, 83, 78)
    pdf.multi_cell(right_w, 5, _safe(right), align="R")
    pdf.set_y(max(left_bottom, pdf.get_y()))


def cv_to_pdf(cv: Profile) -> bytes:
    pdf = ResumePDF(format="A4")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    epw = pdf.w - pdf.l_margin - pdf.r_margin

    contact = cv.contact
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(28, 25, 23)
    pdf.multi_cell(epw, 9, _safe(contact.full_name or "Resume"))

    bits = [contact.email, contact.phone, contact.location, contact.linkedin, contact.github, contact.website]
    line = "  |  ".join(bit for bit in bits if bit)
    if line:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(68, 64, 60)
        pdf.multi_cell(epw, 5, _safe(line))
    pdf.ln(2)

    def heading(title: str) -> None:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(28, 25, 23)
        pdf.cell(epw, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        y = pdf.get_y()
        pdf.set_draw_color(28, 25, 23)
        pdf.line(pdf.l_margin, y, pdf.l_margin + epw, y)
        pdf.ln(2)

    if cv.summary:
        heading("Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(28, 25, 23)
        pdf.multi_cell(epw, 5, _safe(cv.summary))

    if cv.skills:
        heading("Skills")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(28, 25, 23)
        pdf.multi_cell(epw, 5, _safe("  |  ".join(cv.skills)))

    if cv.experience:
        heading("Experience")
        for role in cv.experience:
            left = " - ".join(part for part in [role.title, role.company] if part)
            when = " - ".join(part for part in [role.start, role.end or ("Present" if role.current else "")] if part)
            _row(pdf, left, when)
            if role.location:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(68, 64, 60)
                pdf.multi_cell(epw, 4, _safe(role.location))
            pdf.set_text_color(28, 25, 23)
            pdf.set_font("Helvetica", "", 10)
            for bullet in role.bullets:
                pdf.multi_cell(epw, 5, _safe(f"-  {bullet}"))
            pdf.ln(1)

    if cv.projects:
        heading("Projects")
        for project in cv.projects:
            _row(pdf, project.name, project.url)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(28, 25, 23)
            if project.description:
                pdf.multi_cell(epw, 5, _safe(project.description))
            for bullet in project.bullets:
                pdf.multi_cell(epw, 5, _safe(f"-  {bullet}"))
            pdf.ln(1)

    if cv.education:
        heading("Education")
        for edu in cv.education:
            degree = " in ".join(part for part in [edu.degree, edu.field] if part)
            line = " - ".join(part for part in [degree, edu.school] if part)
            when = " - ".join(part for part in [edu.start, edu.end] if part)
            _row(pdf, line, when)
            if edu.details:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(28, 25, 23)
                pdf.multi_cell(epw, 5, _safe(edu.details))

    if cv.certifications:
        heading("Certifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(28, 25, 23)
        for cert in cv.certifications:
            parts = [cert.name, cert.issuer, f"({cert.year})" if cert.year else ""]
            pdf.multi_cell(epw, 5, _safe(" - ".join(part for part in parts if part)))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def letter_to_pdf(cv: Profile, letter: str, job_title: str = "", company: str = "") -> bytes:
    pdf = ResumePDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    epw = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(28, 25, 23)
    pdf.multi_cell(epw, 7, _safe(cv.contact.full_name or ""))
    bits = [cv.contact.email, cv.contact.phone, cv.contact.location]
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(68, 64, 60)
    pdf.multi_cell(epw, 5, _safe("  |  ".join(bit for bit in bits if bit)))
    if job_title or company:
        pdf.multi_cell(epw, 5, _safe(" | ".join(part for part in [job_title, company] if part)))
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(28, 25, 23)
    for para in (letter or "").split("\n\n"):
        text = para.strip()
        if not text:
            continue
        pdf.multi_cell(epw, 6, _safe(text))
        pdf.ln(3)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
