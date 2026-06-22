from __future__ import annotations

import html as _html

import pandas as pd

# ── Colour palette ────────────────────────────────────────────────────────────
_COLORS: dict[str, dict[str, str]] = {
    "red":   {"text": "#A32D2D", "bg": "#FCEBEB", "row": "#FFF8F8"},
    "green": {"text": "#3B6D11", "bg": "#EAF3DE", "row": "#F4FAF0"},
    "amber": {"text": "#854F0B", "bg": "#FAEEDA", "row": "#FFFCF2"},
    "gray":  {"text": "#666",    "bg": "#EFEFEA", "row": "#F9F9F7"},
    "muted": {"text": "#777",    "bg": "#F5F5F0", "row": "#F9F9F7"},
    "blue":  {"text": "#1A4D8F", "bg": "#E8F0FB", "row": "#F0F5FE"},
}

_CSS = """
<style>
/* ── reset ── */
.vc-root * { box-sizing: border-box; font-family: inherit; }

/* ── card ── */
.vc-card {
  border: 1px solid #e8e8e2;
  border-radius: 10px;
  padding: 13px 15px;
  margin-bottom: 12px;
  background: #fff;
}
.vc-card-title {
  font-size: 10px;
  font-weight: 700;
  color: #999;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.vc-card-foot {
  font-size: 10px;
  color: #aaa;
  margin-top: 8px;
}

/* ── kpi grid ── */
.vc-kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}
.vc-kpi {
  background: #f5f5f0;
  border-radius: 8px;
  padding: 10px 12px;
}
.vc-kpi-label {
  font-size: 10px;
  color: #888;
  margin-bottom: 3px;
}
.vc-kpi-val {
  font-size: 19px;
  font-weight: 600;
  color: #222;
  line-height: 1.1;
}
.vc-kpi-delta {
  font-size: 10px;
  font-weight: 700;
  margin-top: 3px;
}

/* ── badge ── */
.vc-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

/* ── insight box ── */
.vc-insight {
  background: #f5f5f0;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 11px;
  color: #444;
  line-height: 1.6;
  margin-bottom: 8px;
}

/* ── two-column layout ── */
.vc-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

/* ── table ── */
.vc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.vc-table th {
  font-size: 10px;
  font-weight: 600;
  color: #999;
  text-align: right;
  padding: 4px 6px;
  border-bottom: 1px solid #e8e8e2;
  white-space: nowrap;
}
.vc-table th.left { text-align: left; }
.vc-table td {
  text-align: right;
  padding: 4px 6px;
  border-bottom: 1px solid #f0f0ec;
  color: #333;
  white-space: nowrap;
}
.vc-table td.left { text-align: left; }
.vc-table tr.total-row td { background: #f5f5f0 !important; font-weight: 700; }
</style>
"""


def inject_css() -> str:
    """Return the shared CSS block. Call once via st.markdown at app start."""
    return _CSS


def badge(text: str, color: str = "gray") -> str:
    """Inline coloured badge."""
    c = _COLORS.get(color, _COLORS["gray"])
    escaped = _html.escape(str(text))
    return (
        f'<span class="vc-badge" '
        f'style="color:{c["text"]};background:{c["bg"]}">'
        f'{escaped}</span>'
    )


def kpi_card(
    label: str,
    value: str | int | float,
    delta: str | None = None,
    color: str = "muted",
) -> str:
    """Single KPI tile. Returns HTML string (wrap in kpi_row for layout)."""
    c = _COLORS.get(color, _COLORS["muted"])
    lbl = _html.escape(str(label))
    val = _html.escape(str(value))
    delta_html = ""
    if delta is not None:
        delta_html = (
            f'<div class="vc-kpi-delta" style="color:{c["text"]}">'
            f'{_html.escape(str(delta))}</div>'
        )
    return (
        f'<div class="vc-kpi">'
        f'<div class="vc-kpi-label">{lbl}</div>'
        f'<div class="vc-kpi-val">{val}</div>'
        f'{delta_html}'
        f'</div>'
    )


def kpi_row(cards: list[str]) -> str:
    """Responsive grid wrapping a list of kpi_card HTML strings."""
    inner = "\n".join(cards)
    return f'<div class="vc-kpi-row">{inner}</div>'


def card(title: str, body_html: str, footnote: str | None = None) -> str:
    """Bordered card with an optional section-label title and footnote."""
    t = _html.escape(str(title))
    foot = (
        f'<div class="vc-card-foot">{_html.escape(str(footnote))}</div>'
        if footnote
        else ""
    )
    return (
        f'<div class="vc-card vc-root">'
        f'<div class="vc-card-title">{t}</div>'
        f'{body_html}'
        f'{foot}'
        f'</div>'
    )


def insight(body_html: str) -> str:
    """Gray reading/insight box."""
    return f'<div class="vc-insight vc-root">{body_html}</div>'


def two_col(left_html: str, right_html: str) -> str:
    """Two-column equal-width grid."""
    return (
        f'<div class="vc-two-col vc-root">'
        f'<div>{left_html}</div>'
        f'<div>{right_html}</div>'
        f'</div>'
    )


def tabla_html(
    df: pd.DataFrame,
    *,
    highlight_rows: dict[int, str] | None = None,
    col_align: dict[str, str] | None = None,
    total_rows: list[int] | None = None,
    highlight_cells: dict[tuple[int, str], str] | None = None,
    first_col_left: bool = True,
) -> str:
    """
    Render a DataFrame as a styled HTML table.

    Parameters
    ----------
    df               : DataFrame to render.
    highlight_rows   : {row_index: color_name} — tints the whole row.
    col_align        : {col_name: 'left'|'right'|'center'} — overrides default.
    total_rows       : list of row indices that get the 'total-row' class.
    highlight_cells  : {(row_index, col_name): color_name} — tints a single cell.
    first_col_left   : align the first column left (default True).
    """
    highlight_rows = highlight_rows or {}
    col_align = col_align or {}
    total_rows = total_rows or []
    highlight_cells = highlight_cells or {}

    cols = list(df.columns)

    def _th_class(i: int, col: str) -> str:
        if col in col_align:
            return col_align[col]
        if first_col_left and i == 0:
            return "left"
        return ""

    def _td_class(i: int, col: str) -> str:
        if col in col_align:
            return col_align[col]
        if first_col_left and i == 0:
            return "left"
        return ""

    # header
    ths = "".join(
        f'<th class="{_th_class(i, c)}">{_html.escape(str(c))}</th>'
        for i, c in enumerate(cols)
    )
    header = f"<thead><tr>{ths}</tr></thead>"

    # body
    rows_html = []
    for row_idx, (_, row) in enumerate(df.iterrows()):
        row_color = highlight_rows.get(row_idx)
        row_bg = _COLORS[row_color]["row"] if row_color in _COLORS else ""
        tr_style = f'style="background:{row_bg}"' if row_bg else ""
        tr_class = "total-row" if row_idx in total_rows else ""
        tr_attrs = f'class="{tr_class}" {tr_style}'.strip()

        tds = []
        for col_idx, col in enumerate(cols):
            cell_color = highlight_cells.get((row_idx, col))
            cell_bg = _COLORS[cell_color]["bg"] if cell_color in _COLORS else ""
            cell_text = _COLORS[cell_color]["text"] if cell_color in _COLORS else ""
            cell_style = ""
            if cell_bg:
                cell_style = f'style="background:{cell_bg};color:{cell_text}"'
            td_class = _td_class(col_idx, col)
            raw = row[col]
            val = "" if pd.isna(raw) else _html.escape(str(raw))
            tds.append(f'<td class="{td_class}" {cell_style}>{val}</td>')

        rows_html.append(f"<tr {tr_attrs}>{''.join(tds)}</tr>")

    body = f"<tbody>{''.join(rows_html)}</tbody>"
    return f'<div class="vc-root"><table class="vc-table">{header}{body}</table></div>'
