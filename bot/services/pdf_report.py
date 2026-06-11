from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from fpdf import FPDF
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator

_DISPLAY_TZ = timezone(timedelta(hours=3))
_FONT_PATH = font_manager.findfont("DejaVu Sans")
_FONT_BOLD_PATH = font_manager.findfont("DejaVu Sans:bold")

# Palette
_PRIMARY = (76, 110, 245)
_PRIMARY_DARK = (45, 75, 200)
_SUCCESS = (34, 168, 102)
_SUCCESS_BG = (224, 246, 235)
_INFO = (76, 110, 245)
_INFO_BG = (228, 233, 254)
_WARNING = (235, 130, 16)
_WARNING_BG = (253, 235, 217)
_DANGER = (224, 58, 62)
_DANGER_BG = (252, 226, 226)
_TEXT = (45, 52, 64)
_MUTED = (130, 138, 150)
_BORDER = (231, 234, 240)
_ROW_ALT = (247, 248, 251)
_WHITE = (255, 255, 255)

_PAGE_WIDTH = 210
_MARGIN = 14
_CONTENT_WIDTH = _PAGE_WIDTH - 2 * _MARGIN


class _ReportPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_draw_color(*_BORDER)
        self.line(_MARGIN, self.get_y(), _PAGE_WIDTH - _MARGIN, self.get_y())
        self.ln(2)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*_MUTED)
        self.cell(0, 6, "Сформировано TeamPilot", align="L")
        self.set_x(-30)
        self.cell(16, 6, f"стр. {self.page_no()}", align="R")


def build_team_report_pdf(report: dict) -> bytes:
    """Renders a team task report (header, stat cards, table, charts) as a PDF."""
    team_name = report.get("teamName") or "Команда"
    totals = report.get("totals") or {}
    members = report.get("members") or []
    daily = report.get("dailyCompleted") or []
    weekday = report.get("weekdayProductivity") or []
    best_performer = report.get("bestPerformer")
    excuse_stats = report.get("excuseStats") or []

    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("DejaVu", "", _FONT_PATH)
    pdf.add_font("DejaVu", "B", _FONT_BOLD_PATH)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.add_page()

    _draw_header(pdf, team_name, report.get("generatedAt"))
    _draw_stat_cards(pdf, totals)

    if best_performer:
        _draw_best_performer(pdf, best_performer)

    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(*_TEXT)
    pdf.cell(0, 10, "По участникам", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    _draw_members_table(pdf, members)
    pdf.ln(6)

    if any(d.get("count", 0) for d in daily):
        chart_png = _build_bar_chart(
            [_format_short_date(d.get("date", "")) for d in daily],
            [d.get("count", 0) for d in daily],
        )
        pdf.set_font("DejaVu", "B", 13)
        pdf.set_text_color(*_TEXT)
        pdf.cell(0, 10, "Закрытые задачи за последние 7 дней", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.image(io.BytesIO(chart_png), w=_CONTENT_WIDTH)
        pdf.ln(4)

    if any(d.get("count", 0) for d in weekday):
        pdf.add_page()
        chart_png = _build_line_chart(
            [d.get("day", "") for d in weekday],
            [d.get("count", 0) for d in weekday],
        )
        pdf.set_font("DejaVu", "B", 13)
        pdf.set_text_color(*_TEXT)
        pdf.cell(0, 10, "Результативность по дням недели", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.image(io.BytesIO(chart_png), w=_CONTENT_WIDTH)
        pdf.ln(4)

    if excuse_stats:
        pdf.set_font("DejaVu", "B", 13)
        pdf.set_text_color(*_TEXT)
        pdf.cell(0, 10, "Больничные и отгулы за последний месяц", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        _draw_excuse_table(pdf, excuse_stats)

    return bytes(pdf.output())


def _draw_header(pdf: FPDF, team_name: str, generated_at: str | None) -> None:
    band_height = 28
    pdf.set_fill_color(*_PRIMARY)
    pdf.rect(0, 0, _PAGE_WIDTH, band_height, style="F")

    pdf.set_xy(_MARGIN, 7)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(_CONTENT_WIDTH, 10, f"Отчёт по команде «{team_name}»", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(_MARGIN)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(_CONTENT_WIDTH, 6, f"Сформирован: {_format_generated_at(generated_at)}")

    pdf.set_y(band_height + 8)


def _draw_stat_cards(pdf: FPDF, totals: dict) -> None:
    cards = [
        ("Всего задач", totals.get("totalTasks", 0), _INFO, _INFO_BG),
        ("Закрыто", totals.get("completedTasks", 0), _SUCCESS, _SUCCESS_BG),
        ("В работе", totals.get("activeTasks", 0), _PRIMARY_DARK, _INFO_BG),
        ("Просрочено", totals.get("overdueTasks", 0), _DANGER, _DANGER_BG),
    ]

    gap = 4
    card_w = (_CONTENT_WIDTH - gap * (len(cards) - 1)) / len(cards)
    card_h = 24
    y = pdf.get_y()

    for i, (label, value, accent, bg) in enumerate(cards):
        x = _MARGIN + i * (card_w + gap)
        pdf.set_fill_color(*bg)
        pdf.rect(x, y, card_w, card_h, style="F", round_corners=True, corner_radius=2.5)

        pdf.set_xy(x, y + 4)
        pdf.set_text_color(*accent)
        pdf.set_font("DejaVu", "B", 18)
        pdf.cell(card_w, 10, str(value), align="C")

        pdf.set_xy(x, y + 15)
        pdf.set_text_color(*_MUTED)
        pdf.set_font("DejaVu", "", 9)
        pdf.cell(card_w, 6, label, align="C")

    pdf.set_y(y + card_h + 8)
    pdf.set_x(_MARGIN)


def _draw_members_table(pdf: FPDF, members: list[dict]) -> None:
    headers = ["Участник", "Всего", "Закрыто", "В работе", "Просрочено"]
    col_widths = [_CONTENT_WIDTH - 4 * 28, 28, 28, 28, 28]
    row_h = 9

    pdf.set_font("DejaVu", "B", 10)
    pdf.set_fill_color(*_PRIMARY)
    pdf.set_text_color(*_WHITE)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, row_h, header, fill=True, align="C")
    pdf.ln(row_h)

    pdf.set_font("DejaVu", "", 10)
    if not members:
        pdf.set_text_color(*_MUTED)
        pdf.set_draw_color(*_BORDER)
        pdf.cell(_CONTENT_WIDTH, row_h, "Нет данных", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        return

    pdf.set_draw_color(*_BORDER)
    for i, member in enumerate(members):
        pdf.set_text_color(*_TEXT)
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(*_ROW_ALT)

        username = _truncate(str(member.get("username", "—")), 38)
        pdf.cell(col_widths[0], row_h, f" {username}", border="B", fill=fill)

        overdue = member.get("overdueTasks", 0)
        values = [
            member.get("totalTasks", 0),
            member.get("completedTasks", 0),
            member.get("activeTasks", 0),
        ]
        for value, width in zip(values, col_widths[1:4]):
            pdf.cell(width, row_h, str(value), border="B", align="C", fill=fill)

        if overdue:
            pdf.set_text_color(*_DANGER)
            pdf.set_font("DejaVu", "B", 10)
        pdf.cell(col_widths[4], row_h, str(overdue), border="B", align="C", fill=fill)
        if overdue:
            pdf.set_font("DejaVu", "", 10)

        pdf.ln(row_h)


def _draw_best_performer(pdf: FPDF, best_performer: dict) -> None:
    username = best_performer.get("username", "—")
    completed = best_performer.get("completedTasks", 0)

    band_h = 14
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*_SUCCESS_BG)
    pdf.rect(x, y, _CONTENT_WIDTH, band_h, style="F", round_corners=True, corner_radius=2.5)

    pdf.set_xy(x + 4, y)
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(*_SUCCESS)
    pdf.cell(_CONTENT_WIDTH - 8, band_h, f"★ Лучший работник: {username} — {completed} задач закрыто", align="L")

    pdf.set_y(y + band_h + 6)
    pdf.set_x(_MARGIN)


def _draw_excuse_table(pdf: FPDF, excuse_stats: list[dict]) -> None:
    headers = ["Участник", "Больничные/отгулы"]
    col_widths = [_CONTENT_WIDTH - 50, 50]
    row_h = 9

    pdf.set_font("DejaVu", "B", 10)
    pdf.set_fill_color(*_PRIMARY)
    pdf.set_text_color(*_WHITE)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, row_h, header, fill=True, align="C")
    pdf.ln(row_h)

    pdf.set_font("DejaVu", "", 10)
    pdf.set_draw_color(*_BORDER)
    for i, stat in enumerate(excuse_stats):
        pdf.set_text_color(*_TEXT)
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(*_ROW_ALT)

        username = _truncate(str(stat.get("username", "—")), 38)
        pdf.cell(col_widths[0], row_h, f" {username}", border="B", fill=fill)
        pdf.cell(col_widths[1], row_h, str(stat.get("count", 0)), border="B", align="C", fill=fill)
        pdf.ln(row_h)


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _build_bar_chart(labels: list[str], counts: list[int]) -> bytes:
    accent = tuple(c / 255 for c in _PRIMARY)

    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    fig.patch.set_facecolor("white")

    bars = ax.bar(labels, counts, color=accent, width=0.5, zorder=3)

    top = max(counts) if counts else 0
    ax.set_ylim(bottom=0, top=(top * 1.3 if top else 1))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#E7EAF0", linewidth=0.8, zorder=0)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#D5D9E0")
    ax.tick_params(axis="both", length=0, labelsize=10, colors="#828A96")

    for bar, count in zip(bars, counts):
        if count:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (top * 0.04 if top else 0.05),
                str(count),
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="#2D3440",
            )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


def _build_line_chart(labels: list[str], counts: list[int]) -> bytes:
    accent = tuple(c / 255 for c in _PRIMARY)

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    fig.patch.set_facecolor("white")

    ax.plot(labels, counts, color=accent, linewidth=2.5, marker="o", markersize=7,
            markerfacecolor=accent, markeredgecolor="white", markeredgewidth=1.5, zorder=3)
    ax.fill_between(range(len(labels)), counts, color=accent, alpha=0.12, zorder=2)

    top = max(counts) if counts else 0
    ax.set_ylim(bottom=0, top=(top * 1.3 if top else 1))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#E7EAF0", linewidth=0.8, zorder=0)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#D5D9E0")
    ax.tick_params(axis="both", length=0, labelsize=11, colors="#828A96")

    for x, count in enumerate(counts):
        ax.text(
            x,
            count + (top * 0.05 if top else 0.05),
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#2D3440",
        )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


def _format_short_date(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m")
    except ValueError:
        return iso_date


def _format_generated_at(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.astimezone(_DISPLAY_TZ).strftime("%d.%m.%Y %H:%M")
