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

    # ── Metrics ───────────────────────────────────────────────────────────────
    scored_metrics = filter_and_rank(
        portfolio["metrics"], active_tags, min_score=1, max_items=6)
    # Pad to 6 if fewer matched
    if len(scored_metrics) < 6:
        fallback = [m for m in portfolio["metrics"] if m not in scored_metrics]
        scored_metrics += fallback[: 6 - len(scored_metrics)]
    story.append(metric_strip(scored_metrics[:6], styles))
    story.append(Spacer(1, 4 * mm))

    # ── Profile ───────────────────────────────────────────────────────────────
    story += section_heading("Profile", styles)
    variants = portfolio["profile"].get("variants", {})
    profile_text = variants.get(
        focus_label,
        portfolio["profile"]["core"]
    )
    story.append(Paragraph(profile_text, styles["body"]))

    # ── Governance & Advisory (if relevant) ───────────────────────────────────
    gov_items = filter_and_rank(
        portfolio["governance_advisory"], active_tags, min_score=1, max_items=8)
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
        portfolio["grants"], active_tags, min_score=1, max_items=6)
    if grant_items:
        story += section_heading("Grants & Funded Projects", styles)
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

    # ── UoM Collaborations (if relevant) ──────────────────────────────────────
    uom_items = filter_and_rank(
        portfolio["uom_collaborations"], active_tags, min_score=1, max_items=6)
    if uom_items:
        story += section_heading("Collaborations with University of Manchester", styles)
        for item in uom_items:
            story.append(Paragraph(f"\u2022  {item['text']}", styles["bullet"]))

    # ── Partnerships ──────────────────────────────────────────────────────────
    partner_items = filter_and_rank(
        portfolio["partnerships"], active_tags, min_score=1, max_items=8)
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

    book_items = filter_and_rank(pubs["books"], active_tags, min_score=1, max_items=5)
    fc_items   = filter_and_rank(pubs["books_forthcoming"], active_tags, min_score=1, max_items=3)
    ch_items   = filter_and_rank(pubs["chapters"], active_tags, min_score=1, max_items=4)
    ja_items   = filter_and_rank(pubs["journal_articles"], active_tags, min_score=1, max_items=4)
    jo_items   = filter_and_rank(pubs["journalism"], active_tags, min_score=1, max_items=3)

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
        portfolio["keynotes"], active_tags, min_score=1, max_items=16)
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
        portfolio["editorial"], active_tags, min_score=1, max_items=6)
    if ed_items:
        story += section_heading("Editorial & Review", styles)
        for e in ed_items:
            story.append(Paragraph(f"\u2022  {e['text']}", styles["bullet"]))

    # ── Media ─────────────────────────────────────────────────────────────────
    media_highlights = filter_and_rank(
        portfolio["media"]["highlights"], active_tags, min_score=1, max_items=4)
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
