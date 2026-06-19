from datetime import datetime
from io import BytesIO
from fpdf import FPDF


class ExecutivePDF(FPDF):
    def header(self):
        self.set_fill_color(17, 24, 39)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Win11Ready Executive Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_text_color(120, 120, 120)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _safe_text(value):
    if value is None:
        return ""
    return str(value).encode("latin-1", "replace").decode("latin-1")


def _metric_card(pdf, label, value, x, y, w=44, h=24):
    pdf.set_xy(x, y)
    pdf.set_fill_color(31, 41, 55)
    pdf.set_draw_color(75, 85, 99)
    pdf.rect(x, y, w, h, "DF")
    pdf.set_text_color(209, 213, 219)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(x + 3, y + 4)
    pdf.cell(w - 6, 5, _safe_text(label))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(x + 3, y + 12)
    pdf.cell(w - 6, 7, _safe_text(value))


def _section_title(pdf, title):
    pdf.ln(7)
    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(17, 24, 39)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)


def _write_table(pdf, headers, rows, widths):
    pdf.set_fill_color(31, 41, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for header, width in zip(headers, widths):
        pdf.cell(width, 7, _safe_text(header), border=1, fill=True)
    pdf.ln()

    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Helvetica", "", 8)
    fill = False
    for row in rows:
        pdf.set_fill_color(243, 244, 246 if fill else 255)
        for value, width in zip(row, widths):
            pdf.cell(width, 7, _safe_text(value)[:35], border=1, fill=fill)
        pdf.ln()
        fill = not fill


def generate_executive_pdf(
    assessment_name,
    organization_name,
    prepared_by,
    total,
    ready,
    not_ready,
    readiness_score,
    readiness_grade,
    overall_risk_score,
    replacement_count,
    fixable_count,
    estimated_replacement_cost,
    category_counts,
    failure_counts,
    remediation_df,
    manufacturer_summary,
    model_summary,
):
    """Generate a modern executive PDF report and return it as bytes."""
    pdf = ExecutivePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 10, _safe_text(assessment_name or "Windows 11 Readiness Assessment"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(75, 85, 99)
    pdf.cell(0, 6, _safe_text(f"Prepared for: {organization_name or 'Not specified'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe_text(f"Prepared by: {prepared_by or 'Not specified'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe_text(f"Report date: {datetime.now().strftime('%Y-%m-%d')}"), new_x="LMARGIN", new_y="NEXT")

    y = 58
    _metric_card(pdf, "Readiness", f"{readiness_score}%", 10, y)
    _metric_card(pdf, "Grade", readiness_grade, 57, y)
    _metric_card(pdf, "Risk", f"{overall_risk_score}/100", 104, y)
    _metric_card(pdf, "Replacement Cost", f"${estimated_replacement_cost:,.0f}", 151, y)

    pdf.set_y(92)
    _section_title(pdf, "Executive Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(31, 41, 55)
    summary = (
        f"{total} devices were assessed. {ready} devices are ready for Windows 11 and "
        f"{not_ready} require remediation. {fixable_count} device(s) appear fixable, while "
        f"{replacement_count} may require replacement. The current readiness grade is {readiness_grade}."
    )
    pdf.multi_cell(0, 6, _safe_text(summary))

    _section_title(pdf, "Readiness Breakdown")
    category_rows = [[category, int(count)] for category, count in category_counts.items()]
    if category_rows:
        _write_table(pdf, ["Category", "Devices"], category_rows, [120, 40])
    else:
        pdf.cell(0, 7, "No category data available.", new_x="LMARGIN", new_y="NEXT")

    _section_title(pdf, "Top Blockers")
    blocker_rows = [[blocker, int(count)] for blocker, count in failure_counts.head(8).items()]
    if blocker_rows:
        _write_table(pdf, ["Blocker", "Affected Devices"], blocker_rows, [120, 40])
    else:
        pdf.cell(0, 7, "No blockers found.", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    _section_title(pdf, "Recommended Actions")
    if remediation_df is not None and not remediation_df.empty:
        rows = remediation_df[["Blocker", "AffectedDevices", "Priority", "RecommendedAction"]].head(8).values.tolist()
        _write_table(pdf, ["Blocker", "Devices", "Priority", "Recommendation"], rows, [46, 20, 25, 95])
    else:
        pdf.cell(0, 7, "No remediation recommendations generated.", new_x="LMARGIN", new_y="NEXT")

    _section_title(pdf, "Manufacturer Summary")
    if manufacturer_summary is not None and not manufacturer_summary.empty:
        rows = manufacturer_summary[["Manufacturer", "Total", "ReadyPercent", "ReplacementRequired"]].head(8).values.tolist()
        _write_table(pdf, ["Manufacturer", "Total", "Ready %", "Replace"], rows, [70, 30, 30, 30])
    else:
        pdf.cell(0, 7, "No manufacturer summary available.", new_x="LMARGIN", new_y="NEXT")

    _section_title(pdf, "Top Model Risk Summary")
    if model_summary is not None and not model_summary.empty:
        rows = model_summary[["Model", "Total", "ReadyPercent", "ReplacementRequired"]].head(8).values.tolist()
        _write_table(pdf, ["Model", "Total", "Ready %", "Replace"], rows, [80, 25, 30, 30])
    else:
        pdf.cell(0, 7, "No model summary available.", new_x="LMARGIN", new_y="NEXT")

    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    return bytes(pdf_bytes)
