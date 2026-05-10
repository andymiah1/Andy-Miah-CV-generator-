"""
builder.py — Assembles a tailored CV as a PDF using ReportLab.
"""

from __future__ import annotations
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from generator.scorer import filter_and_rank, filter_bullets


# ── Colour palette ────────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#1A2744")
TEAL  = colors.HexColor("#006D77")
MID   = colors.HexColor("#333333")
LIGHT = colors.HexColor("#777777")
RULE  = colors.HexColor("#80CED7")
PALE  = colors.HexColor("#E8F4F5")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


# ── Style sheet ───────────────────────────────────────────────────────────────
def make_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("name", fontSize=28, leading=32,
                               textColor=NAVY, fontName="Helvetica-Bold",
                               spaceAfter=2),
        "credentials": ParagraphStyle("credentials", fontSize=9, leading=12,
                                      textColor=LIGHT, fontName="Helvetica",
                                      spaceAfter=2),
        "title": ParagraphStyle("title", fontSize=11, leading=14,
                                textColor=TEAL, fontName="Helvetica-Bold",
                                spaceAfter=2),
        "tagline": ParagraphStyle("tagline", fontSize=9, leading=12,
                                  textColor=MID, fontName="Helvetica-Oblique",
                                  spaceAfter=4),
        "meta": ParagraphStyle("meta", fontSize=8, leading=10,
                               textColor=LIGHT, fontName="Helvetica",
                               spaceAfter=0),
        "section": ParagraphStyle("section", fontSize=9, leading=11,
                                  textColor=TEAL, fontName="Helvetica-Bold",
                                  spaceBefore=10, spaceAfter=3),
        "role_title": ParagraphStyle("role_title", fontSize=9, leading=11,
                                     textColor=NAVY, fontName="Helvetica-Bold",
                                     spaceBefore=7, spaceAfter=1),
        "role_meta": ParagraphStyle("role_meta", fontSize=8, leading=10,
                                    textColor=TEAL, fontName="Helvetica",
                                    spaceAfter=2),
        "bullet": ParagraphStyle("bullet", fontSize=8.5, leading=11,
                                 textColor=MID, fontName="Helvetica",
                                 leftIndent=10, firstLineIndent=-8,
                                 spaceBefore=1, spaceAfter=1),
        "body": ParagraphStyle("body", fontSize=8.5, leading=12,
                               textColor=MID, fontName="Helvetica",
                               spaceAfter=4, alignment=TA_JUSTIFY),
        "footer": ParagraphStyle("footer", fontSize=7, leading=9,
                                 textColor=LIGHT, fontName="Helvetica-Oblique",
                                 alignment=TA_CENTER),
    }


def thin_rule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=4, spaceBefore=0)


def section_rule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=3, spaceBefore=0)


# ── Metric strip ──────────────────────────────────────────────────────────────
def metric_strip(metrics: list[dict], styles: dict) -> Table:
    cols = min(len(metrics), 6)
    items = metrics[:cols]
    col_w = (PAGE_W - 2 * MARGIN) / cols

    values = [Paragraph(f"<b>{m['value']}</b>", ParagraphStyle(
        "mv", fontSize=13, leading=15, textColor=TEAL,
        fontName="Helvetica-Bold", alignment=TA_CENTER)) for m in items]
    labels = [Paragraph(m["label"], ParagraphStyle(
        "ml", fontSize=6.5, leading=8, textColor=MID,
        fontName="Helvetica", alignment=TA_CENTER)) for m in items]

    table = Table(
        [values, labels],
        colWidths=[col_w] * cols,
        rowHeights=[16, 10]
    )
    table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PALE),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


# ── Section helpers ───────────────────────────────────────────────────────────
def section_heading(title: str, styles: dict) -> list:
    return [
        Paragraph(title.upper(), styles["section"]),
        section_rule(),
    ]


def role_block(title: str, org: str, dates: str,
               bullets: list[str], styles: dict) -> list:
    # Title + org on one line, dates right-aligned via a table
    title_cell = Paragraph(
        f'<b>{title}</b>  <font color="#006D77">{org}</font>',
        ParagraphStyle("rt2", fontSize=9, leading=11, textColor=NAVY,
                       fontName="Helvetica-Bold", spaceBefore=7, spaceAfter=0))
    dates_cell = Paragraph(
        f'<i>{dates}</i>',
        ParagraphStyle("rd", fontSize=8, leading=11, textColor=LIGHT,
                       fontName="Helvetica-Oblique", alignment=TA_RIGHT,
                       spaceBefore=7, spaceAfter=0))
    t = Table([[title_cell, dates_cell]],
              colWidths=[PAGE_W - 2 * MARGIN - 40 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    elements = [t]
    for b in bullets:
        elements.append(Paragraph(f"\u2022  {b}", styles["bullet"]))
    return elements


# ── Main builder ──────────────────────────────────────────────────────────────
def build_cv(
    portfolio: dict,
    active_tags: list[str],
    focus_label: str,
    output_path: str,
) -> str:
    """
    Build a PDF CV tailored to active_tags, save to output_path.
    Returns the output path.
    """
    styles = make_styles()
    identity = portfolio["identity"]
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(identity["name"].upper(), styles["name"]))
    story.append(Paragraph(identity["credentials"], styles["credentials"]))
    story.append(Paragraph(
        f"{identity['title']}  ·  {identity['institution']}",
        styles["title"]))
    story.append(Paragraph(identity["tagline"], styles["tagline"]))
    story.append(Paragraph(
        f"{identity['website']}  ·  {identity['location']}",
        styles["meta"]))
    story.append(Spacer(1, 3 * mm))
    story.append(thin_rule())
    story.append(Spacer(1, 2 * mm))

    # ── Metrics — dynamically calculated ────────────────────────────────────
    import re as _re

    def _calc_grant_total(grants):
        """Sum direct PI/Co-I grant income, excluding oversight and duplicates."""
        total = 0
        for g in grants:
            amt = g.get("amount", "")
            role = g.get("role", "").lower()
            title = g.get("title", "").lower()
            if "oversight" in amt.lower(): continue
            if "£4.5m total" in amt.lower(): continue
            if "committee member" in role and "snsf" in title: continue
            for num, unit in _re.findall(r"£([\d,.]+)\s*([mk]?)", amt.lower()):
                n = float(num.replace(",", ""))
                if unit == "m": n *= 1_000_000
                elif unit == "k": n *= 1_000
                total += n
        return total

    _grant_total = _calc_grant_total(portfolio.get("grants", []))
    _keynote_count = len(portfolio.get("keynotes", []))
    _keynote_value = _keynote_count * 1000
    _total_investment = _grant_total + _keynote_value
    _pub_count = sum(len(portfolio["publications"].get(k, []))
                     for k in ["journal_articles", "chapters", "books"])

    # Update dynamic metrics values before scoring
    dynamic_metrics = []
    for m in portfolio.get("metrics", []):
        m = dict(m)  # copy
        label = m.get("label", "")
        if "Direct Grant Income" in label:
            m["value"] = f"£{_grant_total/1e6:.1f}m+"
        elif "Total Portfolio Investment" in label:
            m["value"] = f"£{_total_investment/1e6:.1f}m+"
        elif "Invited Talks" in label:
            m["value"] = f"{_keynote_count}+"
        elif "Peer-reviewed" in label:
            m["value"] = f"{_pub_count}+"
        dynamic_metrics.append(m)

    scored_metrics = filter_and_rank(
        dynamic_metrics, active_tags, min_score=1, max_items=6)
    if len(scored_metrics) < 6:
        fallback = [m for m in dynamic_metrics if m not in scored_metrics]
        scored_metrics += fallback[: 6 - len(scored_metrics)]
    story.append(metric_strip(scored_metrics[:6], styles))
    story.append(Spacer(1, 4 * mm))

    # ── Profile ───────────────────────────────────────────────────────────────
    story += section_heading("Profile", styles)
    variants = portfolio["profile"].get("variants", {})
    focus_areas = portfolio.get("focus_areas", {})

    # Try exact match first, then score each variant against active_tags
    profile_text = variants.get(focus_label)
    if not profile_text:
        best_score, best_variant = 0, None
        for variant_key, variant_text in variants.items():
            variant_tags = set(focus_areas.get(variant_key, []))
            score = len(variant_tags & set(active_tags))
            if score > best_score:
                best_score, best_variant = score, variant_text
        profile_text = best_variant or portfolio["profile"]["core"]

    # Render as multiple paragraphs (split on blank line)
    for para_text in profile_text.split("\n\n"):
        para_text = para_text.strip()
        if para_text:
            story.append(Paragraph(para_text, styles["body"]))
            story.append(Spacer(1, 2 * mm))

    # ── Governance & Advisory (if relevant) ───────────────────────────────────
    gov_items = filter_and_rank(
        portfolio["governance_advisory"], active_tags, min_score=1, max_items=10)
    if gov_items:
        story += section_heading("Governance & Advisory Roles", styles)
        rows = []
        for item in gov_items:
            title_p = Paragraph(
                f'<b>{item["title"]}</b>',
                ParagraphStyle("gt", fontSize=8.5, textColor=NAVY,
                               fontName="Helvetica-Bold", leading=11))
            org_p = Paragraph(
                item["org"],
                ParagraphStyle("go", fontSize=8.5, textColor=TEAL,
                               fontName="Helvetica", leading=11))
            dates_p = Paragraph(
                f'<i>{item["dates"]}</i>',
                ParagraphStyle("gd", fontSize=8, textColor=LIGHT,
                               fontName="Helvetica-Oblique",
                               leading=11, alignment=TA_RIGHT))
            rows.append([title_p, org_p, dates_p])
        col_w = PAGE_W - 2 * MARGIN
        t = Table(rows, colWidths=[col_w * 0.3, col_w * 0.5, col_w * 0.2])
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW",     (0, -1), (-1, -1), 0, colors.white),
        ]))
        story.append(t)

    # ── Grants ────────────────────────────────────────────────────────────────
    grant_items = filter_and_rank(
        portfolio["grants"], active_tags, min_score=1, max_items=8,
        query=focus_label)
    if grant_items:
        story += section_heading("Research Funding", styles)

        # Investment summary table if available
        inv = portfolio.get("investment_summary")
        if inv:
            summary_rows = [
                [
                    Paragraph("<b>Category</b>", ParagraphStyle("th", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10)),
                    Paragraph("<b>Role</b>", ParagraphStyle("th", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10)),
                    Paragraph("<b>Cash Value</b>", ParagraphStyle("th", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                    Paragraph("<b>Est. In-Kind</b>", ParagraphStyle("th", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                    Paragraph("<b>Total</b>", ParagraphStyle("th", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                ],
                [
                    Paragraph("Competitive Research Grants", ParagraphStyle("tc", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("PI", ParagraphStyle("tc", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("£3,374,500", ParagraphStyle("tc", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("—", ParagraphStyle("tc", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("£3,374,500", ParagraphStyle("tc", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                ],
                [
                    Paragraph("Competitive Research Grants", ParagraphStyle("tc2", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("Co-I", ParagraphStyle("tc2", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("£10,618,000+", ParagraphStyle("tc2", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("—", ParagraphStyle("tc2", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("£10,618,000+", ParagraphStyle("tc2", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                ],
                [
                    Paragraph("Strategic Institutional Investment", ParagraphStyle("tc3", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("Lead", ParagraphStyle("tc3", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10)),
                    Paragraph("£861,500", ParagraphStyle("tc3", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("£4,328,000", ParagraphStyle("tc3", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                    Paragraph("£5,189,500", ParagraphStyle("tc3", fontSize=7.5, textColor=MID, fontName="Helvetica", leading=10, alignment=2)),
                ],
                [
                    Paragraph("<b>Total (PI/Lead)</b>", ParagraphStyle("tf", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10)),
                    Paragraph("", ParagraphStyle("tf", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10)),
                    Paragraph("<b>£4,236,000</b>", ParagraphStyle("tf", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                    Paragraph("<b>£4,328,000</b>", ParagraphStyle("tf", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                    Paragraph("<b>£8,564,000</b>", ParagraphStyle("tf", fontSize=7.5, textColor=TEAL, fontName="Helvetica-Bold", leading=10, alignment=2)),
                ],
            ]
            col_w = PAGE_W - 2 * MARGIN
            inv_table = Table(
                summary_rows,
                colWidths=[col_w*0.38, col_w*0.08, col_w*0.18, col_w*0.18, col_w*0.18]
            )
            inv_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0),  PALE),
                ("BACKGROUND",    (0, 4), (-1, 4),  PALE),
                ("LINEBELOW",     (0, 0), (-1, 0),  0.5, TEAL),
                ("LINEABOVE",     (0, 4), (-1, 4),  0.5, TEAL),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(inv_table)
            story.append(Spacer(1, 4 * mm))

        # Selected grants list
        story.append(Paragraph("Selected Grants", ParagraphStyle(
            "gsub", fontSize=8.5, textColor=MID, fontName="Helvetica-Bold",
            leading=11, spaceBefore=4, spaceAfter=3)))
        for g in grant_items:
            label = f"<b>{g['dates']}</b>  ·  <b>{g['title']}</b>  —  {g['funder']} ({g['role']})  ·  {g['amount']}"
            story.append(Paragraph(label, styles["bullet"]))
            if g.get("description"):
                story.append(Paragraph(g["description"], ParagraphStyle(
                    "gdesc", fontSize=8, leading=10, textColor=LIGHT,
                    fontName="Helvetica-Oblique", leftIndent=10, spaceAfter=2)))

    # ── Career History ────────────────────────────────────────────────────────
    story += section_heading("Career History", styles)
    ranked_roles = filter_and_rank(
        portfolio["appointments"], active_tags, min_score=0)  # always show all roles
    for appt in ranked_roles:
        bullets = filter_bullets(appt.get("bullets", []), active_tags)
        block = role_block(
            appt["title"], appt["institution"], appt["dates"],
            bullets, styles)
        story += block

    # ── Partnerships ──────────────────────────────────────────────────────────
    partner_items = filter_and_rank(
        portfolio["partnerships"], active_tags, min_score=1, max_items=10)
    if partner_items:
        story += section_heading("Key External Partnerships", styles)
        left = partner_items[: len(partner_items) // 2 + len(partner_items) % 2]
        right = partner_items[len(partner_items) // 2 + len(partner_items) % 2:]
        left_cells = [Paragraph(
            f"\u2022  <b>{p['org']}</b> — {p['description']}",
            styles["bullet"]) for p in left]
        right_cells = [Paragraph(
            f"\u2022  <b>{p['org']}</b> — {p['description']}",
            styles["bullet"]) for p in right]
        # Pad to equal length
        while len(right_cells) < len(left_cells):
            right_cells.append(Paragraph("", styles["bullet"]))
        col_w = (PAGE_W - 2 * MARGIN) / 2
        rows = [[l, r] for l, r in zip(left_cells, right_cells)]
        t = Table(rows, colWidths=[col_w - 3 * mm, col_w + 3 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(t)

    # ── Publications ──────────────────────────────────────────────────────────
    pubs = portfolio["publications"]
    story += section_heading("Selected Publications", styles)

    book_items = filter_and_rank(pubs["books"], active_tags, min_score=1, max_items=6, query=focus_label)
    fc_items   = filter_and_rank(pubs["books_forthcoming"], active_tags, min_score=1, max_items=4, query=focus_label)
    ch_items   = filter_and_rank(pubs["chapters"], active_tags, min_score=1, max_items=8, query=focus_label)
    ja_items   = filter_and_rank(pubs["journal_articles"], active_tags, min_score=1, max_items=8, query=focus_label)
    jo_items   = filter_and_rank(pubs["journalism"], active_tags, min_score=1, max_items=8, query=focus_label)

    sub_style = ParagraphStyle("psub", fontSize=8.5, textColor=NAVY,
                                fontName="Helvetica-Bold", leading=11,
                                spaceBefore=5, spaceAfter=2)

    if book_items:
        story.append(Paragraph("Books", sub_style))
        for p in book_items:
            story.append(Paragraph(f"\u2022  {p['citation']}", styles["bullet"]))
    if fc_items:
        story.append(Paragraph("Forthcoming Books", sub_style))
        for p in fc_items:
            story.append(Paragraph(f"\u2022  {p['citation']}", styles["bullet"]))
    if ja_items:
        story.append(Paragraph("Journal Articles", sub_style))
        for p in ja_items:
            story.append(Paragraph(f"\u2022  {p['citation']}", styles["bullet"]))
    if ch_items:
        story.append(Paragraph("Book Chapters", sub_style))
        for p in ch_items:
            story.append(Paragraph(f"\u2022  {p['citation']}", styles["bullet"]))
    if jo_items:
        story.append(Paragraph("Journalism & Public Writing", sub_style))
        for p in jo_items:
            story.append(Paragraph(f"\u2022  {p['citation']}", styles["bullet"]))

    # ── Selected Keynotes ─────────────────────────────────────────────────────
    keynote_items = filter_and_rank(
        portfolio["keynotes"], active_tags, min_score=1, max_items=30)
    if keynote_items:
        story += section_heading("Selected Keynotes & Invited Talks", styles)
        # Two-column layout
        left = keynote_items[: len(keynote_items) // 2 + len(keynote_items) % 2]
        right = keynote_items[len(keynote_items) // 2 + len(keynote_items) % 2:]
        while len(right) < len(left):
            right.append({"text": ""})
        col_w = (PAGE_W - 2 * MARGIN) / 2
        rows = [
            [Paragraph(f"\u2022  {l['text']}", styles["bullet"]),
             Paragraph(f"\u2022  {r['text']}" if r["text"] else "", styles["bullet"])]
            for l, r in zip(left, right)
        ]
        t = Table(rows, colWidths=[col_w - 3 * mm, col_w + 3 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(t)

    # ── Awards ────────────────────────────────────────────────────────────────
    award_items = filter_and_rank(
        portfolio["awards"], active_tags, min_score=0)  # always show all
    story += section_heading("Awards & Recognition", styles)
    for a in award_items:
        story.append(Paragraph(f"\u2022  {a['text']}", styles["bullet"]))

    # ── Editorial & Review ────────────────────────────────────────────────────
    ed_items = filter_and_rank(
        portfolio["editorial"], active_tags, min_score=1, max_items=8)
    if ed_items:
        story += section_heading("Editorial & Review", styles)
        for e in ed_items:
            story.append(Paragraph(f"\u2022  {e['text']}", styles["bullet"]))

    # ── Media ─────────────────────────────────────────────────────────────────
    media_highlights = filter_and_rank(
        portfolio["media"]["highlights"], active_tags, min_score=1, max_items=10)
    story += section_heading("Media Presence", styles)
    story.append(Paragraph(portfolio["media"]["summary"], styles["body"]))
    for m in media_highlights:
        story.append(Paragraph(f"\u2022  {m['text']}", styles["bullet"]))

    # ── Education ─────────────────────────────────────────────────────────────
    story += section_heading("Education & Qualifications", styles)
    for ed in portfolio["education"]:
        block = role_block(ed["degree"], ed["institution"], ed["dates"],
                           [ed["note"]] if ed.get("note") else [], styles)
        story += block

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(thin_rule())
    story.append(Paragraph(
        f"References available on request  ·  andymiah.net  ·  "
        f"Generated {datetime.today().strftime('%B %Y')}  ·  Focus: {focus_label}",
        styles["footer"]))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Andy Miah CV — {focus_label}",
        author="Andy Miah",
    )
    doc.build(story)
    return output_path


# ── Teaching CV builder ────────────────────────────────────────────────────────
def build_teaching_cv(
    portfolio: dict,
    output_path: str,
) -> str:
    """
    Build a dedicated teaching-focused CV.
    Sections ordered: Profile → Teaching → Doctoral Supervision →
    Career → Selected Publications → Keynotes → Awards → Education
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4

    styles = make_styles()
    identity = portfolio["identity"]
    story = []
    active_tags = portfolio["focus_areas"].get("teaching-cv", [])
    focus_label = "teaching-cv"

    MARGIN = 18 * mm

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(identity["name"].upper(), styles["name"]))
    story.append(Paragraph(identity["credentials"], styles["credentials"]))
    story.append(Paragraph(
        f"{identity['title']}  ·  {identity['institution']}",
        styles["title"]))
    story.append(Paragraph(
        "Teaching Portfolio & Academic CV",
        ParagraphStyle("tptag", fontSize=9, leading=11,
                       textColor=TEAL, fontName="Helvetica-Oblique",
                       spaceAfter=4)))
    story.append(Paragraph(
        f"{identity['website']}  ·  {identity['location']}",
        styles["meta"]))
    story.append(Spacer(1, 3 * mm))
    story.append(thin_rule())
    story.append(Spacer(1, 2 * mm))

    # ── Teaching summary stats ────────────────────────────────────────────────
    from generator.scorer import filter_and_rank
    teaching_metrics = [
        {"value": "25+ yrs", "label": "University Teaching"},
        {"value": "10+",     "label": "Courses Designed"},
        {"value": "10",      "label": "PhD Students Supervised/Examined"},
        {"value": "15+",     "label": "Institutions Taught At"},
        {"value": "120",     "label": "Max Cohort Size"},
        {"value": "10 yrs",  "label": "RCA Visiting Professorship"},
    ]
    story.append(metric_strip(teaching_metrics, styles))
    story.append(Spacer(1, 4 * mm))

    # ── Profile ───────────────────────────────────────────────────────────────
    story += section_heading("Profile", styles)
    profile_text = portfolio["profile"]["variants"].get(
        "teaching-cv", portfolio["profile"]["core"])
    for para_text in profile_text.split("\n\n"):
        para_text = para_text.strip()
        if para_text:
            story.append(Paragraph(para_text, styles["body"]))
            story.append(Spacer(1, 2 * mm))

    # ── Teaching (ALL items, no cap) ──────────────────────────────────────────
    teaching_items = portfolio.get("teaching", [])
    # Filter to only structured items (title/institution/dates/notes format)
    structured = [t for t in teaching_items
                  if t.get("title") and t.get("institution")]
    if structured:
        story += section_heading("Teaching Appointments & Courses", styles)
        for t in structured:
            block = role_block(
                t.get("title", ""),
                t.get("institution", ""),
                t.get("dates", ""),
                [t["notes"]] if t.get("notes") else [],
                styles)
            story += block

    # ── Teaching history detail (always shown) ────────────────────────────────
    story += section_heading("Programme & Module Contributions", styles)

    prog_data = [
        ("University of Salford", "2015 – present", [
            "MSc Science Communication & Future Media — Co-Director. Modules: Science Communication as a Way of Life; Science Writing, Backpack Journalism & Mobile Media; Global Challenges in Science Communication; Live Performance; Public Involvement & Citizen Science",
            "MSc Biotechnology — Critical Issues in Science Communication",
            "MSc Wildlife Conservation — Science Communication as a Way of Life; Contemporary Issues",
            "BSc Biomedical Science — Bioethics (Level 5); Translational Research Skills",
            "BSc Wildlife Conservation — Frontiers in Wildlife Biology (Drones); Study Skills",
            "BSc across School — Professional Skills & Practice (Science Communication)",
        ]),
        ("Royal College of Art — MA Design Interactions", "2006 – 2016", [
            "Annual masterclasses for Professor Anthony Dunne: Posthuman Designs (2006); NanoCulture: On Speculation & Paranoia (2008); Superheros (2009); Drone Culture (2014); Living a Posthuman Life (2015); Life After Extinction (2016)",
        ]),
        ("University of the West of Scotland", "2002 – 2014", [
            "Becoming Posthuman (Year 4 Honours, class 16) — course designer and lead lecturer. External examiner commendation for innovative delivery",
            "Cyberculture (Year 2, class 120) — coordinator and lead lecturer. Topics: CyberIdentity, CyberCinema, VideoGaming, CyberPolitics",
            "Sport & Spectacle (Year 3, class 100) — lecturer. Topics: technology, doping, Olympic politics, extreme sports",
            "Digital Environments (Year 2/3, class 20) — lecturer. Macromedia Design Suite, Dreamweaver, Photoshop",
        ]),
        ("University of Glasgow — Graduate School of Biomedical & Life Sciences", "2002 – 2005", [
            "Ethics & Bioethics in Science & Medicine — associate lecturer (cohort: 120 PhD students across biomedical and life sciences). Topics: xenotransplantation, ecosystem health, human genetics, experimental research ethics",
        ]),
        ("Guest & Visiting Teaching", "2002 – present", [
            "Central St Martins — MA Material Futures: BioDesign and Future Humans (2017); Posthuman Futures (2014)",
            "UCL — Bioethics & Sport MSc (2007); Beyond Bioethics: The Culture of Posthumanity (2007)",
            "Glasgow School of Art — New Media Ethics and Biotechnology (2006); Posthumanism (2005)",
            "Oregon State University (2016); Edinburgh College of Art (2010); Glasgow School of Art (2010)",
            "St Mary's College San Francisco: The Posthuman Athlete (2008); Gene Doping and the Future of Sport (2004)",
            "International Academy of Sports Science & Technology, Switzerland: Social/Ethical issues in Technology & Sport (2004); Gene Doping (2003)",
            "EPFL Lausanne (2003); State University of New York (2002); Anglia Ruskin LLM International Sport Law (2001, 2004, 2007)",
        ]),
    ]

    for inst, dates, bullets in prog_data:
        block = role_block(inst, "", dates, bullets, styles)
        story += block

    # ── Doctoral Supervision ──────────────────────────────────────────────────
    story += section_heading("Doctoral Supervision & Examination", styles)

    story.append(Paragraph("Director of Studies", ParagraphStyle(
        "dsub", fontSize=8.5, textColor=MID, fontName="Helvetica-Bold",
        leading=11, spaceBefore=5, spaceAfter=2)))
    for b in [
        "Max Kimano — Science Communication at Science Festivals, University of Salford (2025–)",
        "Jennifer Jones — Social Media and the Olympic Games, UWS (2009–)",
        "Bettina Hörmann — Public Engagement with Nanotechnology Ethics, UWS (2007–)",
        "Ana Adi — New Media at the Beijing Olympics, UWS (2007–) [Fulbright alumna]",
    ]:
        story.append(Paragraph(f"\u2022  {b}", styles["bullet"]))

    story.append(Paragraph("External Examiner", ParagraphStyle(
        "dsub2", fontSize=8.5, textColor=MID, fontName="Helvetica-Bold",
        leading=11, spaceBefore=8, spaceAfter=2)))
    for b in [
        "Yun Peng, University of Glasgow (2020)",
        "Debra Brasset, Warwick University (2019)",
        "James McFarlane, Warwick University (2018)",
        "Ege Sezen, Lancaster University (2017)",
        "Laura Ager, Salford University (2016)",
        "John Pinder, Salford University (2015)",
        "Bryce Dyer, Bournemouth University (2013)",
        "Natasha Vita-More, Plymouth University (2012)",
        "Janet Bennett, Cardiff Metropolitan University (2012)",
        "Neil McPherson, Glasgow Caledonian University (2010)",
    ]:
        story.append(Paragraph(f"\u2022  {b}", styles["bullet"]))

    # ── Career ────────────────────────────────────────────────────────────────
    story += section_heading("Academic Appointments", styles)
    for appt in portfolio["appointments"]:
        bullets = [b["text"] for b in appt.get("bullets", [])][:4]
        block = role_block(
            appt["title"], appt["institution"], appt["dates"],
            bullets, styles)
        story += block

    # ── Selected publications relevant to teaching ─────────────────────────────
    pubs = portfolio["publications"]
    story += section_heading("Selected Publications", styles)
    all_pubs = (
        filter_and_rank(pubs["books"], active_tags, min_score=1, max_items=5,
                        query=focus_label) +
        filter_and_rank(pubs["chapters"], active_tags, min_score=1, max_items=4,
                        query=focus_label) +
        filter_and_rank(pubs["journal_articles"], active_tags, min_score=1,
                        max_items=4, query=focus_label)
    )
    for pub in all_pubs:
        story.append(Paragraph(f"\u2022  {pub['citation']}", styles["bullet"]))

    # ── Education ─────────────────────────────────────────────────────────────
    story += section_heading("Education & Qualifications", styles)
    for ed in portfolio["education"]:
        block = role_block(ed["degree"], ed["institution"], ed["dates"],
                           [ed["note"]] if ed.get("note") else [], styles)
        story += block

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(thin_rule())
    story.append(Paragraph(
        f"References available on request  ·  andymiah.net  ·  Teaching Portfolio",
        styles["footer"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    import os
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="Andy Miah — Teaching CV",
        author="Andy Miah",
    )
    doc.build(story)
    return output_path
