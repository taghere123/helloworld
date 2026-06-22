"""
Dashboard Vida Cash — Streamlit Community Cloud.

Data is read from Google Drive using a Service Account.
Credentials and folder_id are stored in st.secrets — never in the repo.
"""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from modules.combinaciones import (
    combinaciones_criticas,
    tabla_combinaciones,
    tabla_evolucion_combinacion,
    top_ganadoras,
    top_perdedoras,
)
from modules.data_loader import parse_data
from modules.drive_loader import load_from_drive
from modules.filters import (
    DIAS_SEMANA_ES,
    FUENTE_A_CANAL_MACRO,
    MESES_ES,
    PERIODOS,
    TIPOS_VISTA,
    _unique_vals,
    apply_filters,
)
from modules.funnel import (
    tabla_calidad_leads,
    tabla_comparativo_cvr,
    tabla_comparativo_pxq,
    tabla_fuente_leads,
    tabla_funnel,
)
from modules.insights import generar_insights
from modules.ui_components import (
    badge,
    card,
    inject_css,
    insight,
    kpi_card,
    kpi_row,
    tabla_html,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Vida Cash",
    page_icon="📊",
    layout="wide",
)
st.markdown(inject_css(), unsafe_allow_html=True)

# ── Password gate ──────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated", False):
    st.title("Dashboard Vida Cash")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar", type="primary"):
        try:
            expected = st.secrets["app"]["password"]
        except KeyError:
            st.error("El secret `app.password` no está configurado.")
            st.stop()
        if pwd == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# ── Sidebar header ─────────────────────────────────────────────────────────────
st.sidebar.title("Dashboard Vida Cash")

if st.sidebar.button("🔄 Recargar ahora", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ── Load data from Drive ───────────────────────────────────────────────────────
try:
    leads_b, ventas_b, leads_mod, ventas_mod = load_from_drive()
except Exception as exc:
    st.error(f"**Error al conectar con Google Drive:**\n\n{exc}")
    st.stop()

try:
    df_leads_raw, df_ventas_raw, inv_leads, inv_ventas = parse_data(leads_b, ventas_b)
except Exception as exc:
    st.error(f"**Error al procesar los archivos Excel:**\n\n{exc}")
    st.stop()

# ── Sidebar — file metadata ────────────────────────────────────────────────────
def _fmt_drive_time(iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso

with st.sidebar.expander("📁 Archivos en Drive", expanded=False):
    st.write(f"**Leads.xlsx**  \n{_fmt_drive_time(leads_mod)}")
    st.write(f"**Ventas.xlsx**  \n{_fmt_drive_time(ventas_mod)}")
    meses_leads = sorted(df_leads_raw["Mes"].unique())
    meses_ventas = sorted(df_ventas_raw["Mes venta"].unique())
    st.write(f"**Meses Leads:** {meses_leads}")
    st.write(f"**Meses Ventas:** {meses_ventas}")
    if inv_leads:
        st.warning(f"Leads excluidos: **{inv_leads:,}**")
    if inv_ventas:
        st.warning(f"Ventas excluidas: **{inv_ventas:,}**")

st.sidebar.markdown("---")

# ── Sidebar — Filters ─────────────────────────────────────────────────────────
st.sidebar.markdown("## Filtros")

periodo = st.sidebar.selectbox("Periodo", PERIODOS, index=2)  # default: Mensual
tipo_vista = st.sidebar.radio("Tipo de vista", TIPOS_VISTA, index=0)
st.sidebar.markdown("---")

with st.sidebar.expander("📅 Rango de fechas", expanded=False):
    has_dates = "fecha_lead" in df_leads_raw.columns and df_leads_raw["fecha_lead"].notna().any()
    if has_dates:
        min_date = df_leads_raw["fecha_lead"].dropna().dt.date.min()
        max_date = df_leads_raw["fecha_lead"].dropna().dt.date.max()
        fecha_inicio = st.date_input("Fecha inicio", value=min_date, min_value=min_date, max_value=max_date)
        fecha_fin = st.date_input("Fecha fin", value=max_date, min_value=min_date, max_value=max_date)
    else:
        st.info("FechaAsignacion no disponible en los datos.")
        fecha_inicio = fecha_fin = None

with st.sidebar.expander("🗓️ Día / Mes", expanded=False):
    meses_sel = st.multiselect("Mes", options=list(MESES_ES.values()), default=[], placeholder="Todos")
    dias_mes_sel = st.multiselect("Día del mes", options=list(range(1, 32)), default=[], placeholder="Todos")
    dias_semana_sel = st.multiselect("Día de semana", options=list(DIAS_SEMANA_ES.values()), default=[], placeholder="Todos")

with st.sidebar.expander("📦 Sub producto", expanded=False):
    sub_producto_sel = st.multiselect("Sub producto", options=["Vida Cash", "Endosos"], default=[], placeholder="Todos")

with st.sidebar.expander("📡 Canal", expanded=False):
    canales_macro_disp = sorted(set(FUENTE_A_CANAL_MACRO.values()) | {"Otro"})
    if "canal_macro" in df_leads_raw.columns:
        canales_macro_disp = _unique_vals(df_leads_raw, "canal_macro")
    canal_sel = st.multiselect("Canal", options=canales_macro_disp, default=[], placeholder="Todos")

    sub_canales_disp: list[str] = []
    if "Fuente Anuncio" in df_leads_raw.columns:
        sub_canales_disp = sorted(df_leads_raw["Fuente Anuncio"].dropna().str.strip().unique().tolist())
    sub_canal_sel = st.multiselect("Sub canal", options=sub_canales_disp, default=[], placeholder="Todos", disabled=not sub_canales_disp)

    SSC_COLS = ("Sub Canal", "SubCanal", "Sub Sub Canal", "sub_sub_canal")
    ssc_col = next((c for c in SSC_COLS if c in df_leads_raw.columns), None)
    if ssc_col:
        sub_sub_canal_sel = st.multiselect("Sub sub canal", options=_unique_vals(df_leads_raw, ssc_col), default=[], placeholder="Todos")
    else:
        st.caption("Sub sub canal: no disponible en los datos actuales.")
        sub_sub_canal_sel = []

with st.sidebar.expander("📞 Call center", expanded=False):
    CC_COLS = ("Call Center", "CallCenter", "call_center", "Centro Llamadas")
    cc_col = next((c for c in CC_COLS if c in df_leads_raw.columns or c in df_ventas_raw.columns), None)
    if cc_col:
        src = df_leads_raw if cc_col in df_leads_raw.columns else df_ventas_raw
        call_center_sel = st.multiselect("Call center", options=_unique_vals(src, cc_col), default=[], placeholder="Todos")
    else:
        st.caption("Call center: no disponible en los datos actuales.")
        call_center_sel = []

# ── Apply filters ──────────────────────────────────────────────────────────────
df_leads, df_ventas = apply_filters(
    df_leads_raw,
    df_ventas_raw,
    fecha_inicio=fecha_inicio if has_dates else None,
    fecha_fin=fecha_fin if has_dates else None,
    dias_semana=dias_semana_sel or None,
    dias_mes=dias_mes_sel or None,
    meses=meses_sel or None,
    sub_producto=sub_producto_sel or None,
    canal=canal_sel or None,
    sub_canal=sub_canal_sel or None,
    sub_sub_canal=sub_sub_canal_sel or None,
    call_center=call_center_sel or None,
)

_active = sum(
    bool(x) for x in [
        meses_sel, dias_mes_sel, dias_semana_sel, sub_producto_sel,
        canal_sel, sub_canal_sel, sub_sub_canal_sel, call_center_sel,
        (fecha_inicio if has_dates else None),
    ]
)
if _active:
    st.sidebar.caption(f"✅ {_active} filtro(s) activo(s) — {len(df_leads):,} leads · {len(df_ventas):,} ventas")

# ── Pre-compute funnel tables ──────────────────────────────────────────────────
_kw = dict(periodo=periodo, tipo_vista=tipo_vista)
df_funnel_total = tabla_funnel(df_leads, df_ventas, **_kw)
df_funnel_vc    = tabla_funnel(df_leads, df_ventas, tipo="vida_cash", **_kw)
df_funnel_end   = tabla_funnel(df_leads, df_ventas, tipo="endosos", **_kw)
df_comb         = tabla_combinaciones(df_ventas, df_leads, tipo="vida_cash")

# ── Insights banner ────────────────────────────────────────────────────────────
_COLOR_MAP = {"rojo": "red", "amarillo": "amber", "verde": "green"}
insights = generar_insights(df_funnel_vc, df_funnel_end, df_funnel_total, df_comb, df_leads)
if insights:
    st.subheader("🔍 Insights del mes")
    for ins in insights:
        color = _COLOR_MAP.get(ins["tipo"], "gray")
        st.markdown(
            insight(f"{badge(ins['tipo'].upper(), color)}&nbsp;&nbsp;{ins['texto']}"),
            unsafe_allow_html=True,
        )
    st.divider()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _funnel_highlight(df: pd.DataFrame) -> dict[int, str]:
    """Row colour based on ΔCVR sign."""
    hl: dict[int, str] = {}
    if "ΔCVR (%)" in df.columns:
        for i, val in enumerate(df["ΔCVR (%)"]):
            if pd.notna(val):
                hl[i] = "green" if float(val) > 0 else "red"
    return hl


def _cascada(df_l: pd.DataFrame, df_v: pd.DataFrame):
    leads_doc = df_l[["NumeroDocumento", "Mes"]].copy()
    ventas_doc = (
        df_v[["Póliza", "N° de doc.", "Mes venta"]]
        .copy()
        .rename(columns={"N° de doc.": "NumeroDocumento"})
    )
    merged = ventas_doc.merge(leads_doc, on="NumeroDocumento", how="left")
    n_unmatched = int(merged["Mes"].isna().sum())
    matched = merged.dropna(subset=["Mes"]).copy()
    matched["Mes"] = matched["Mes"].astype(int)
    matched["Mes venta"] = matched["Mes venta"].astype(int)
    matched["lag"] = matched["Mes venta"] - matched["Mes"]
    matched = matched[matched["lag"] >= 0].sort_values("lag").drop_duplicates(subset=["Póliza"])
    if matched.empty:
        return pd.DataFrame(), pd.DataFrame(), n_unmatched
    matrix = matched.groupby(["Mes", "Mes venta"]).size().unstack(fill_value=0)
    matrix.index.name = "Mes lead"
    leads_cnt = df_l.groupby("Mes").size()
    rows = []
    for ml in sorted(matrix.index):
        nl = int(leads_cnt.get(ml, 0))
        nv = int(matrix.loc[ml].sum())
        rows.append({
            "Mes lead": ml,
            "Leads": nl,
            "Ventas atribuidas": nv,
            "CVR atribuido (%)": round(nv / nl * 100, 2) if nl else 0.0,
        })
    cvr_df = pd.DataFrame(rows)
    cvr_df["CVR acumulado (%)"] = (
        cvr_df["Ventas atribuidas"].cumsum() / cvr_df["Leads"].cumsum() * 100
    ).round(2)
    return matrix, cvr_df, n_unmatched


# ── Conversion tab ─────────────────────────────────────────────────────────────
def _tab_conversion(df_l: pd.DataFrame, df_v: pd.DataFrame, per: str, tv: str):
    st.header("Conversión")

    total_leads  = len(df_l)
    total_ventas = len(df_v)
    cvr_overall  = total_ventas / total_leads * 100 if total_leads else 0.0
    pxq_total    = float(df_v["Prima_Anual"].sum()) if not df_v.empty else 0.0

    df_trend = tabla_funnel(df_l, df_v, periodo=per, tipo_vista=tv)
    cvr_delta_str: str | None = None
    cvr_color = "muted"
    if len(df_trend) >= 2:
        delta_cvr = float(df_trend.iloc[-1]["CVR (%)"]) - float(df_trend.iloc[-2]["CVR (%)"])
        sign = "+" if delta_cvr >= 0 else ""
        cvr_delta_str = f"{sign}{delta_cvr:.2f} pp vs período anterior"
        cvr_color = "green" if delta_cvr > 0 else "red"

    st.markdown(kpi_row([
        kpi_card("Leads", f"{total_leads:,}"),
        kpi_card("Ventas", f"{total_ventas:,}"),
        kpi_card("CVR", f"{cvr_overall:.2f}%", delta=cvr_delta_str, color=cvr_color),
        kpi_card("PxQ total (S/)", f"{pxq_total:,.0f}"),
    ]), unsafe_allow_html=True)

    st.divider()

    st.subheader(f"Tendencia — {per} | {tv}")
    if not df_trend.empty:
        hl = _funnel_highlight(df_trend)
        st.markdown(
            card(f"Tendencia {per}", tabla_html(df_trend, highlight_rows=hl)),
            unsafe_allow_html=True,
        )
        if "CVR (%)" in df_trend.columns and len(df_trend) > 1:
            st.line_chart(df_trend.set_index("Periodo")["CVR (%)"], height=200)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        rows_sp = []
        for sp_label, sp_tipo in [("Vida Cash", "vida_cash"), ("Endosos", "endosos")]:
            df_sp = tabla_funnel(df_l, df_v, tipo=sp_tipo, periodo=per, tipo_vista=tv)
            if not df_sp.empty and df_sp["Leads"].sum():
                rows_sp.append({
                    "Sub producto": sp_label,
                    "Leads": int(df_sp["Leads"].sum()),
                    "Ventas": int(df_sp["Pólizas"].sum()),
                    "CVR (%)": round(df_sp["Pólizas"].sum() / df_sp["Leads"].sum() * 100, 2),
                    "PxQ/día (S/)": round(df_sp["PxQ/día (S/)"].mean(), 0),
                })
        if rows_sp:
            st.markdown(
                card("Por Sub producto", tabla_html(pd.DataFrame(rows_sp))),
                unsafe_allow_html=True,
            )

    with col2:
        if "Fuente Anuncio" in df_l.columns:
            fuente_grp = (
                df_l.groupby(df_l["Fuente Anuncio"].str.lower().str.strip())
                .agg(Leads=("NumeroDocumento", "count"))
                .reset_index()
                .rename(columns={"Fuente Anuncio": "Sub canal"})
                .sort_values("Leads", ascending=False)
            )
            st.markdown(
                card("Por Sub canal (Fuente Anuncio)", tabla_html(fuente_grp)),
                unsafe_allow_html=True,
            )
        else:
            st.info("Sin datos de Fuente Anuncio.")

    if "canal_macro" in df_l.columns:
        macro_rows = [
            {"Canal": cm, "Leads": int(len(df_l[df_l["canal_macro"] == cm]))}
            for cm in sorted(df_l["canal_macro"].dropna().unique())
        ]
        st.markdown(
            card("Por Canal macro (Organic / Paid / Owned)", tabla_html(pd.DataFrame(macro_rows))),
            unsafe_allow_html=True,
        )


# ── Tabs ───────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🔄 Conversión",
    "1 · Total",
    "2 · Vida Cash",
    "3 · Endosos",
    "4 · Comparativo CVR",
    "5 · Combinaciones PxQ",
    "6 · Cascada",
    "7 · CVR por combinación",
    "8 · Insights",
])

# ── Tab 0 — Conversión ─────────────────────────────────────────────────────────
with tabs[0]:
    _tab_conversion(df_leads, df_ventas, periodo, tipo_vista)

# ── Tab 1 — Total ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("Total consolidado — todos los canales")
    st.markdown(
        tabla_html(df_funnel_total, highlight_rows=_funnel_highlight(df_funnel_total)),
        unsafe_allow_html=True,
    )

# ── Tab 2 — Vida Cash ──────────────────────────────────────────────────────────
with tabs[2]:
    st.header("Vida Cash")
    st.markdown(
        tabla_html(df_funnel_vc, highlight_rows=_funnel_highlight(df_funnel_vc)),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Calidad de leads (%)")
        d = tabla_calidad_leads(df_leads, tipo="vida_cash")
        if not d.empty:
            st.markdown(tabla_html(d.reset_index()), unsafe_allow_html=True)
        else:
            st.info("Sin datos de TipoLead.")
    with c2:
        st.subheader("Fuente de leads (volumen)")
        d = tabla_fuente_leads(df_leads, tipo="vida_cash")
        if not d.empty:
            st.markdown(tabla_html(d.reset_index()), unsafe_allow_html=True)
        else:
            st.info("Sin datos de Fuente Anuncio.")

# ── Tab 3 — Endosos ────────────────────────────────────────────────────────────
with tabs[3]:
    st.header("Endosos")
    st.markdown(
        tabla_html(df_funnel_end, highlight_rows=_funnel_highlight(df_funnel_end)),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Calidad de leads (%)")
        d = tabla_calidad_leads(df_leads, tipo="endosos")
        if not d.empty:
            st.markdown(tabla_html(d.reset_index()), unsafe_allow_html=True)
        else:
            st.info("Sin datos de TipoLead.")
    with c2:
        st.subheader("Fuente de leads (volumen)")
        d = tabla_fuente_leads(df_leads, tipo="endosos")
        if not d.empty:
            st.markdown(tabla_html(d.reset_index()), unsafe_allow_html=True)
        else:
            st.info("Sin datos de Fuente Anuncio.")

# ── Tab 4 — Comparativo CVR ────────────────────────────────────────────────────
with tabs[4]:
    st.header("Comparativo CVR y PxQ/día")
    st.subheader("CVR: Vida Cash vs Endosos vs Total")
    st.markdown(
        tabla_html(tabla_comparativo_cvr(df_funnel_vc, df_funnel_end, df_funnel_total)),
        unsafe_allow_html=True,
    )
    st.subheader("PxQ/día y participación de Endosos")
    st.markdown(
        tabla_html(tabla_comparativo_pxq(df_funnel_vc, df_funnel_end, df_funnel_total)),
        unsafe_allow_html=True,
    )

# ── Tab 5 — Combinaciones PxQ ─────────────────────────────────────────────────
with tabs[5]:
    st.header("Combinaciones PxQ — Periodo de Pago × % Dev.")
    st.caption("PRE = meses 1-3 · POST = meses 4-6 · Normalizado por días · Ordenado por Δ PxQ/día (peores primero)")
    _dc  = ["Periodo de Pago", "% Dev.", "vol_pre_dia", "vol_post_dia", "prima_pre", "prima_post", "pxq_pre_dia", "pxq_post_dia", "delta_pxq", "delta_pxq_pct"]
    _lbl = {"vol_pre_dia": "Vol/día PRE", "vol_post_dia": "Vol/día POST", "prima_pre": "Prima PRE", "prima_post": "Prima POST", "pxq_pre_dia": "PxQ/día PRE", "pxq_post_dia": "PxQ/día POST", "delta_pxq": "Δ PxQ/día", "delta_pxq_pct": "Δ PxQ (%)"}
    _fmt = {"Vol/día PRE": "{:.2f}", "Vol/día POST": "{:.2f}", "Prima PRE": "S/{:,.0f}", "Prima POST": "S/{:,.0f}", "PxQ/día PRE": "S/{:,.0f}", "PxQ/día POST": "S/{:,.0f}", "Δ PxQ/día": "S/{:,.0f}", "Δ PxQ (%)": "{:.1f}%"}
    _av  = [c for c in _dc if c in df_comb.columns]

    def _show_comb(df: pd.DataFrame) -> None:
        st.dataframe(df[_av].rename(columns=_lbl).style.format(_fmt, na_rep="—"), use_container_width=True, hide_index=True)

    st.subheader("Top 15 perdedoras")
    _show_comb(top_perdedoras(df_comb, 15))
    st.subheader("Top 10 ganadoras")
    _show_comb(top_ganadoras(df_comb, 10))
    with st.expander("Ver todas"):
        _show_comb(df_comb)

# ── Tab 6 — Cascada ────────────────────────────────────────────────────────────
with tabs[6]:
    st.header("Cascada de ventas — cohortes por mes de lead")
    matrix, cvr_df, n_um = _cascada(df_leads, df_ventas)
    if n_um:
        st.info(f"**{n_um:,}** ventas sin lead identificado.")
    if matrix.empty:
        st.warning("Sin matches entre Leads y Ventas por NumeroDocumento.")
    else:
        st.subheader("Matriz cohorte (mes lead → mes venta)")
        st.dataframe(matrix, use_container_width=True)
        st.subheader("CVR atribuido por cohorte")
        st.markdown(tabla_html(cvr_df.reset_index(drop=True)), unsafe_allow_html=True)

# ── Tab 7 — CVR por combinación crítica ───────────────────────────────────────
with tabs[7]:
    st.header("CVR mensual por combinación crítica")
    st.caption("Top 5 perdedoras + top 3 ganadoras calculadas dinámicamente.")
    criticas = combinaciones_criticas(df_comb)
    if criticas.empty:
        st.warning("Sin combinaciones suficientes.")
    else:
        for _, row in criticas.iterrows():
            plazo, dev = row["Periodo de Pago"], row["% Dev."]
            pct = row.get("delta_pxq_pct")
            icon = ("🔴" if pd.notna(pct) and pct < 0 else "🟢") if pd.notna(pct) else "⚪"
            label = f"{icon} {plazo}a / {dev}%  —  Δ {pct:.0f}%" if pd.notna(pct) else f"{plazo}a / {dev}%"
            with st.expander(label, expanded=False):
                df_ev = tabla_evolucion_combinacion(df_ventas, df_leads, plazo, dev)
                if not df_ev.empty:
                    st.markdown(tabla_html(df_ev.reset_index(drop=True)), unsafe_allow_html=True)
                else:
                    st.write("Sin datos.")

# ── Tab 8 — Insights ──────────────────────────────────────────────────────────
with tabs[8]:
    st.header("Insights del mes — detalle")
    if not insights:
        st.success("No se detectaron alertas para el último mes disponible.")
    else:
        for ins in insights:
            color = _COLOR_MAP.get(ins["tipo"], "gray")
            st.markdown(
                insight(f"{badge(ins['tipo'].upper(), color)}&nbsp;&nbsp;{ins['texto']}"),
                unsafe_allow_html=True,
            )
    with st.expander("Ver umbrales"):
        st.markdown("""
| Regla | Umbral |
|---|---|
| Caída de CVR | Δ CVR < −15% vs mes anterior |
| Combo perdedora | Δ PxQ % < −50% y PxQ PRE > S/1,000/mes |
| Caída de fuente | Vol < 50% del mes anterior (mín. 50 leads previos) |
| Calidad leads | % Alto bajando ≥ 2 meses consecutivos |
| Resiliencia 125% dev | \|Δ medio\| < 15% y Δ otros < −15% |
""")
