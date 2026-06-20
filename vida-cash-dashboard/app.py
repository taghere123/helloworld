"""
Dashboard Vida Cash — Streamlit Community Cloud.

Data is read from Google Drive using a Service Account.
Credentials and folder_id are stored in st.secrets (configured in the
Streamlit Cloud UI — never committed to the repo).
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

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
from modules.funnel import (
    tabla_calidad_leads,
    tabla_comparativo_cvr,
    tabla_comparativo_pxq,
    tabla_fuente_leads,
    tabla_funnel,
)
from modules.insights import generar_insights

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Vida Cash",
    page_icon="📊",
    layout="wide",
)

# ── Password gate ──────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated", False):
    st.title("Dashboard Vida Cash")
    pwd = st.text_input("Contraseña", type="password", key="pwd_input")
    if st.button("Entrar", type="primary"):
        try:
            expected = st.secrets["app"]["password"]
        except KeyError:
            st.error("El secret `app.password` no está configurado en Streamlit Cloud.")
            st.stop()
        if pwd == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Dashboard Vida Cash")
st.sidebar.markdown("---")

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
    df_leads, df_ventas, inv_leads, inv_ventas = parse_data(leads_b, ventas_b)
except Exception as exc:
    st.error(f"**Error al procesar los archivos Excel:**\n\n{exc}")
    st.stop()

# ── Sidebar metadata ───────────────────────────────────────────────────────────
def _fmt_drive_time(iso: str) -> str:
    """Convert Drive ISO-8601 UTC timestamp to a readable local-ish string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso

st.sidebar.markdown("### Archivos en Drive")
st.sidebar.write(f"**Leads.xlsx**  \n{_fmt_drive_time(leads_mod)}")
st.sidebar.write(f"**Ventas.xlsx**  \n{_fmt_drive_time(ventas_mod)}")

meses_leads = sorted(df_leads["Mes"].unique())
meses_ventas = sorted(df_ventas["Mes venta"].unique())
st.sidebar.markdown("### Datos cargados")
st.sidebar.write(f"**Meses Leads:** {meses_leads}")
st.sidebar.write(f"**Meses Ventas:** {meses_ventas}")
if inv_leads:
    st.sidebar.warning(f"Leads excluidos (mes inválido): **{inv_leads:,}**")
if inv_ventas:
    st.sidebar.warning(f"Ventas excluidas (mes inválido): **{inv_ventas:,}**")

# ── Pre-compute tables ─────────────────────────────────────────────────────────
df_funnel_total = tabla_funnel(df_leads, df_ventas)
df_funnel_vc = tabla_funnel(df_leads, df_ventas, tipo="vida_cash")
df_funnel_end = tabla_funnel(df_leads, df_ventas, tipo="endosos")
df_comb = tabla_combinaciones(df_ventas, df_leads, tipo="vida_cash")

# ── Insights banner (before tabs) ─────────────────────────────────────────────
insights = generar_insights(
    df_funnel_vc, df_funnel_end, df_funnel_total, df_comb, df_leads
)
if insights:
    st.subheader("🔍 Insights del mes")
    for ins in insights:
        fn = {"rojo": st.error, "amarillo": st.warning, "verde": st.success}.get(
            ins["tipo"], st.info
        )
        fn(ins["texto"])
    st.divider()

# ── Cascade helper ─────────────────────────────────────────────────────────────
def _cascada(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    leads_doc = df_leads[["NumeroDocumento", "Mes"]].copy()
    ventas_doc = (
        df_ventas[["Póliza", "N° de doc.", "Mes venta"]]
        .copy()
        .rename(columns={"N° de doc.": "NumeroDocumento"})
    )

    merged = ventas_doc.merge(leads_doc, on="NumeroDocumento", how="left")
    n_unmatched = int(merged["Mes"].isna().sum())

    matched = merged.dropna(subset=["Mes"]).copy()
    matched["Mes"] = matched["Mes"].astype(int)
    matched["Mes venta"] = matched["Mes venta"].astype(int)
    matched["lag"] = matched["Mes venta"] - matched["Mes"]
    matched = matched[matched["lag"] >= 0]
    matched = matched.sort_values("lag").drop_duplicates(subset=["Póliza"])

    if matched.empty:
        return pd.DataFrame(), pd.DataFrame(), n_unmatched

    matrix = matched.groupby(["Mes", "Mes venta"]).size().unstack(fill_value=0)
    matrix.index.name = "Mes lead"

    leads_count = df_leads.groupby("Mes").size()
    cvr_rows = []
    for mes_lead in sorted(matrix.index):
        n_l = int(leads_count.get(mes_lead, 0))
        total_v = int(matrix.loc[mes_lead].sum())
        cvr_rows.append(
            {
                "Mes lead": mes_lead,
                "Leads": n_l,
                "Ventas atribuidas": total_v,
                "CVR atribuido (%)": round(total_v / n_l * 100, 2) if n_l else 0.0,
            }
        )
    cvr_df = pd.DataFrame(cvr_rows)
    cvr_df["CVR acumulado (%)"] = (
        cvr_df["Ventas atribuidas"].cumsum() / cvr_df["Leads"].cumsum() * 100
    ).round(2)

    return matrix, cvr_df, n_unmatched


# ── Tabs ───────────────────────────────────────────────────────────────────────
tabs = st.tabs(
    [
        "1 · Total",
        "2 · Vida Cash",
        "3 · Endosos",
        "4 · Comparativo CVR",
        "5 · Combinaciones PxQ",
        "6 · Cascada",
        "7 · CVR por combinación",
        "8 · Insights",
    ]
)

# ── Tab 1 — Total consolidado ──────────────────────────────────────────────────
with tabs[0]:
    st.header("Total consolidado — todos los canales")
    st.dataframe(df_funnel_total, use_container_width=True, hide_index=True)

# ── Tab 2 — Vida Cash ──────────────────────────────────────────────────────────
with tabs[1]:
    st.header("Vida Cash")
    st.dataframe(df_funnel_vc, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Calidad de leads (%)")
        df_cal = tabla_calidad_leads(df_leads, tipo="vida_cash")
        st.dataframe(df_cal, use_container_width=True) if not df_cal.empty else st.info("Sin datos de TipoLead.")
    with col2:
        st.subheader("Fuente de leads (volumen)")
        df_src = tabla_fuente_leads(df_leads, tipo="vida_cash")
        st.dataframe(df_src, use_container_width=True) if not df_src.empty else st.info("Sin datos de Fuente Anuncio.")

# ── Tab 3 — Endosos ────────────────────────────────────────────────────────────
with tabs[2]:
    st.header("Endosos")
    st.dataframe(df_funnel_end, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Calidad de leads (%)")
        df_cal_e = tabla_calidad_leads(df_leads, tipo="endosos")
        st.dataframe(df_cal_e, use_container_width=True) if not df_cal_e.empty else st.info("Sin datos de TipoLead.")
    with col2:
        st.subheader("Fuente de leads (volumen)")
        df_src_e = tabla_fuente_leads(df_leads, tipo="endosos")
        st.dataframe(df_src_e, use_container_width=True) if not df_src_e.empty else st.info("Sin datos de Fuente Anuncio.")

# ── Tab 4 — Comparativo CVR ────────────────────────────────────────────────────
with tabs[3]:
    st.header("Comparativo CVR y PxQ/día")
    st.subheader("CVR: Vida Cash vs Endosos vs Total")
    st.dataframe(
        tabla_comparativo_cvr(df_funnel_vc, df_funnel_end, df_funnel_total),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("PxQ/día y participación de Endosos")
    st.dataframe(
        tabla_comparativo_pxq(df_funnel_vc, df_funnel_end, df_funnel_total),
        use_container_width=True,
        hide_index=True,
    )

# ── Tab 5 — Combinaciones PxQ ─────────────────────────────────────────────────
with tabs[4]:
    st.header("Combinaciones PxQ — Periodo de Pago × % Dev.")
    st.caption("PRE = meses 1-3 · POST = meses 4-6 · Normalizado por días · Ordenado por Δ PxQ/día (peores primero)")

    _display = [
        "Periodo de Pago", "% Dev.",
        "vol_pre_dia", "vol_post_dia",
        "prima_pre", "prima_post",
        "pxq_pre_dia", "pxq_post_dia",
        "delta_pxq", "delta_pxq_pct",
    ]
    _labels = {
        "vol_pre_dia": "Vol/día PRE", "vol_post_dia": "Vol/día POST",
        "prima_pre": "Prima PRE", "prima_post": "Prima POST",
        "pxq_pre_dia": "PxQ/día PRE", "pxq_post_dia": "PxQ/día POST",
        "delta_pxq": "Δ PxQ/día", "delta_pxq_pct": "Δ PxQ (%)",
    }
    _fmt = {
        "Vol/día PRE": "{:.2f}", "Vol/día POST": "{:.2f}",
        "Prima PRE": "S/{:,.0f}", "Prima POST": "S/{:,.0f}",
        "PxQ/día PRE": "S/{:,.0f}", "PxQ/día POST": "S/{:,.0f}",
        "Δ PxQ/día": "S/{:,.0f}", "Δ PxQ (%)": "{:.1f}%",
    }
    avail = [c for c in _display if c in df_comb.columns]

    def _show(df: pd.DataFrame) -> None:
        st.dataframe(
            df[avail].rename(columns=_labels).style.format(_fmt, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Top 15 perdedoras")
    _show(top_perdedoras(df_comb, 15))
    st.subheader("Top 10 ganadoras")
    _show(top_ganadoras(df_comb, 10))
    with st.expander("Ver todas las combinaciones"):
        _show(df_comb)

# ── Tab 6 — Cascada ────────────────────────────────────────────────────────────
with tabs[5]:
    st.header("Cascada de ventas — cohortes por mes de lead")
    matrix, cvr_df, n_unmatched = _cascada(df_leads, df_ventas)
    if n_unmatched:
        st.info(f"**{n_unmatched:,}** ventas sin lead identificado (excluidas de la cascada).")
    if matrix.empty:
        st.warning("No se encontraron matches entre Leads y Ventas por NumeroDocumento.")
    else:
        st.subheader("Matriz cohorte (mes lead → mes venta)")
        st.dataframe(matrix, use_container_width=True)
        st.subheader("CVR atribuido por cohorte")
        st.dataframe(cvr_df, use_container_width=True, hide_index=True)

# ── Tab 7 — CVR por combinación crítica ───────────────────────────────────────
with tabs[6]:
    st.header("CVR mensual por combinación crítica")
    st.caption("Top 5 perdedoras + top 3 ganadoras calculadas dinámicamente por Δ PxQ/día.")
    criticas = combinaciones_criticas(df_comb, n_top=5, n_bottom=3)
    if criticas.empty:
        st.warning("No hay suficientes combinaciones para calcular.")
    else:
        for _, row in criticas.iterrows():
            plazo, dev = row["Periodo de Pago"], row["% Dev."]
            pct = row.get("delta_pxq_pct")
            if pd.notna(pct):
                icon = "🔴" if pct < 0 else "🟢"
                label = f"{icon} {plazo}a / {dev}% — Δ {pct:.0f}%"
            else:
                label = f"{plazo}a / {dev}%"
            with st.expander(label, expanded=False):
                df_evol = tabla_evolucion_combinacion(df_ventas, df_leads, plazo, dev)
                st.dataframe(df_evol, use_container_width=True, hide_index=True) if not df_evol.empty else st.write("Sin datos.")

# ── Tab 8 — Insights detallados ────────────────────────────────────────────────
with tabs[7]:
    st.header("Insights del mes — detalle")
    if not insights:
        st.success("No se detectaron alertas para el último mes disponible.")
    else:
        st.caption("Generados automáticamente con reglas sobre los datos. Sin LLM, sin datos externos.")
        for ins in insights:
            fn = {"rojo": st.error, "amarillo": st.warning, "verde": st.success}.get(
                ins["tipo"], st.info
            )
            fn(ins["texto"])

    with st.expander("Ver umbrales usados"):
        st.markdown(
            """
| Regla | Umbral |
|---|---|
| Caída de CVR (alerta roja) | Δ CVR < −15% vs mes anterior |
| Combinación crítica perdedora | Δ PxQ % < −50% **y** PxQ PRE mensual > S/1,000 |
| Caída de fuente de leads | Vol actual < 50% del anterior, mín. 50 leads previos |
| Calidad leads cayendo | % Alto bajando ≥ 2 meses consecutivos |
| Resiliencia 125% dev | \|Δ medio 125%\| < 15% y Δ medio otros < −15% |
"""
        )
