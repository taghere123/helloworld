"""
Dashboard Vida Cash — Streamlit local app.

Drop Leads.xlsx and Ventas.xlsx in ./data/ and open http://localhost:8501.
Press "Recargar datos" after replacing the files to pick up changes without
restarting the server.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.combinaciones import (
    combinaciones_criticas,
    tabla_combinaciones,
    tabla_evolucion_combinacion,
    top_ganadoras,
    top_perdedoras,
)
from modules.data_loader import DATA_DIR, get_file_mtimes, load_data
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

# ── Cascade helpers ────────────────────────────────────────────────────────────

def _cascada(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """
    Match leads → ventas by document number.

    Returns (cohort_matrix, cvr_table, n_unmatched_ventas).
    """
    leads_doc = df_leads[["NumeroDocumento", "Mes"]].copy()
    ventas_doc = df_ventas[["Póliza", "N° de doc.", "Mes venta"]].copy()
    ventas_doc = ventas_doc.rename(columns={"N° de doc.": "NumeroDocumento"})

    merged = ventas_doc.merge(leads_doc, on="NumeroDocumento", how="left")
    n_unmatched = int(merged["Mes"].isna().sum())

    matched = merged.dropna(subset=["Mes"]).copy()
    matched["Mes"] = matched["Mes"].astype(int)
    matched["Mes venta"] = matched["Mes venta"].astype(int)
    matched["lag"] = matched["Mes venta"] - matched["Mes"]
    matched = matched[matched["lag"] >= 0]
    # Deduplicate by póliza: keep min-lag lead per poliza
    matched = matched.sort_values("lag").drop_duplicates(subset=["Póliza"])

    if matched.empty:
        return pd.DataFrame(), pd.DataFrame(), n_unmatched

    matrix = matched.groupby(["Mes", "Mes venta"]).size().unstack(fill_value=0)
    matrix.index.name = "Mes lead"

    # CVR table
    leads_count = df_leads.groupby("Mes").size()
    cvr_rows = []
    for mes_lead in sorted(matrix.index):
        n_leads = int(leads_count.get(mes_lead, 0))
        total_ventas = int(matrix.loc[mes_lead].sum())
        cvr_atrib = total_ventas / n_leads * 100 if n_leads else 0.0
        cvr_rows.append(
            {
                "Mes lead": mes_lead,
                "Leads": n_leads,
                "Ventas atribuidas": total_ventas,
                "CVR atribuido (%)": round(cvr_atrib, 2),
            }
        )
    cvr_df = pd.DataFrame(cvr_rows)
    # Cumulative CVR (ventas acumuladas / leads de la cohorte)
    cvr_df["CVR acumulado (%)"] = (
        cvr_df["Ventas atribuidas"].cumsum() / cvr_df["Leads"].cumsum() * 100
    ).round(2)

    return matrix, cvr_df, n_unmatched


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Dashboard Vida Cash")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Recargar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("### Archivos fuente")
for fname in ["Leads.xlsx", "Ventas.xlsx"]:
    fpath = DATA_DIR / fname
    if fpath.exists():
        mtime = datetime.datetime.fromtimestamp(fpath.stat().st_mtime)
        st.sidebar.write(f"**{fname}**  \n{mtime.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.sidebar.error(f"{fname} no encontrado en `/data`")


# ── Load data (cached, invalidated by file mtime) ─────────────────────────────
@st.cache_data(show_spinner="Cargando archivos Excel…")
def _cached_load(mtimes: tuple) -> tuple:  # noqa: ARG001
    return load_data()


mtimes = get_file_mtimes()

if None in mtimes:
    st.error(
        "No se encontraron **Leads.xlsx** y/o **Ventas.xlsx** en la carpeta `/data`.\n\n"
        "Copia los archivos allí y recarga la página."
    )
    st.stop()

try:
    df_leads, df_ventas, inv_leads, inv_ventas = _cached_load(mtimes)
except Exception as exc:
    st.error(f"Error al leer los archivos: {exc}")
    st.stop()

# Sidebar metadata
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
        color_map = {"rojo": "error", "amarillo": "warning", "verde": "success"}
        fn = getattr(st, color_map.get(ins["tipo"], "info"))
        fn(ins["texto"])
    st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_labels = [
    "1 · Total",
    "2 · Vida Cash",
    "3 · Endosos",
    "4 · Comparativo CVR",
    "5 · Combinaciones PxQ",
    "6 · Cascada",
    "7 · CVR por combinación",
    "8 · Insights",
]
tabs = st.tabs(tab_labels)

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
        if not df_cal.empty:
            st.dataframe(df_cal, use_container_width=True)
        else:
            st.info("Sin datos de TipoLead.")

    with col2:
        st.subheader("Fuente de leads (volumen)")
        df_src = tabla_fuente_leads(df_leads, tipo="vida_cash")
        if not df_src.empty:
            st.dataframe(df_src, use_container_width=True)
        else:
            st.info("Sin datos de Fuente Anuncio.")

# ── Tab 3 — Endosos ────────────────────────────────────────────────────────────
with tabs[2]:
    st.header("Endosos")
    st.dataframe(df_funnel_end, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Calidad de leads (%)")
        df_cal_e = tabla_calidad_leads(df_leads, tipo="endosos")
        if not df_cal_e.empty:
            st.dataframe(df_cal_e, use_container_width=True)
        else:
            st.info("Sin datos de TipoLead.")

    with col2:
        st.subheader("Fuente de leads (volumen)")
        df_src_e = tabla_fuente_leads(df_leads, tipo="endosos")
        if not df_src_e.empty:
            st.dataframe(df_src_e, use_container_width=True)
        else:
            st.info("Sin datos de Fuente Anuncio.")

# ── Tab 4 — Comparativo CVR ────────────────────────────────────────────────────
with tabs[3]:
    st.header("Comparativo CVR y PxQ/día")

    st.subheader("CVR: Vida Cash vs Endosos vs Total")
    df_cvr_comp = tabla_comparativo_cvr(df_funnel_vc, df_funnel_end, df_funnel_total)
    st.dataframe(df_cvr_comp, use_container_width=True, hide_index=True)

    st.subheader("PxQ/día y participación de Endosos")
    df_pxq_comp = tabla_comparativo_pxq(df_funnel_vc, df_funnel_end, df_funnel_total)
    st.dataframe(df_pxq_comp, use_container_width=True, hide_index=True)

# ── Tab 5 — Combinaciones PxQ ─────────────────────────────────────────────────
with tabs[4]:
    st.header("Combinaciones PxQ — Periodo de Pago × % Dev.")
    st.caption(
        "PRE = meses 1-3 · POST = meses 4-6 · Valores normalizados por días · "
        "Ordenado por Δ PxQ/día (peores primero)"
    )

    display_cols = [
        "Periodo de Pago",
        "% Dev.",
        "vol_pre_dia",
        "vol_post_dia",
        "prima_pre",
        "prima_post",
        "pxq_pre_dia",
        "pxq_post_dia",
        "delta_pxq",
        "delta_pxq_pct",
    ]
    col_labels = {
        "vol_pre_dia": "Vol/día PRE",
        "vol_post_dia": "Vol/día POST",
        "prima_pre": "Prima media PRE",
        "prima_post": "Prima media POST",
        "pxq_pre_dia": "PxQ/día PRE",
        "pxq_post_dia": "PxQ/día POST",
        "delta_pxq": "Δ PxQ/día",
        "delta_pxq_pct": "Δ PxQ (%)",
    }

    available = [c for c in display_cols if c in df_comb.columns]
    df_comb_show = df_comb[available].rename(columns=col_labels)

    st.subheader(f"Top 15 perdedoras")
    perd = top_perdedoras(df_comb, 15)
    perd_show = perd[available].rename(columns=col_labels)
    st.dataframe(
        perd_show.style.format(
            {
                "Vol/día PRE": "{:.2f}",
                "Vol/día POST": "{:.2f}",
                "Prima media PRE": "S/{:,.0f}",
                "Prima media POST": "S/{:,.0f}",
                "PxQ/día PRE": "S/{:,.0f}",
                "PxQ/día POST": "S/{:,.0f}",
                "Δ PxQ/día": "S/{:,.0f}",
                "Δ PxQ (%)": "{:.1f}%",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(f"Top 10 ganadoras")
    gan = top_ganadoras(df_comb, 10)
    gan_show = gan[available].rename(columns=col_labels)
    st.dataframe(
        gan_show.style.format(
            {
                "Vol/día PRE": "{:.2f}",
                "Vol/día POST": "{:.2f}",
                "Prima media PRE": "S/{:,.0f}",
                "Prima media POST": "S/{:,.0f}",
                "PxQ/día PRE": "S/{:,.0f}",
                "PxQ/día POST": "S/{:,.0f}",
                "Δ PxQ/día": "S/{:,.0f}",
                "Δ PxQ (%)": "{:.1f}%",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Ver todas las combinaciones"):
        st.dataframe(
            df_comb_show.style.format(
                {
                    "Vol/día PRE": "{:.2f}",
                    "Vol/día POST": "{:.2f}",
                    "PxQ/día PRE": "S/{:,.0f}",
                    "PxQ/día POST": "S/{:,.0f}",
                    "Δ PxQ/día": "S/{:,.0f}",
                    "Δ PxQ (%)": "{:.1f}%",
                },
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
        )

# ── Tab 6 — Cascada de ventas ──────────────────────────────────────────────────
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
    st.caption(
        "Combinaciones calculadas dinámicamente: top 5 perdedoras + top 3 ganadoras "
        "por Δ PxQ/día absoluto."
    )

    criticas = combinaciones_criticas(df_comb, n_top=5, n_bottom=3)

    if criticas.empty:
        st.warning("No hay suficientes combinaciones para calcular.")
    else:
        for _, row in criticas.iterrows():
            plazo = row["Periodo de Pago"]
            dev = row["% Dev."]
            delta_pct = row.get("delta_pxq_pct")
            label = (
                f"🔴 {plazo}a / {dev}% — Δ {delta_pct:.0f}%"
                if pd.notna(delta_pct) and delta_pct < 0
                else f"🟢 {plazo}a / {dev}% — Δ {delta_pct:.0f}%"
                if pd.notna(delta_pct)
                else f"{plazo}a / {dev}%"
            )
            with st.expander(label, expanded=False):
                df_evol = tabla_evolucion_combinacion(
                    df_ventas, df_leads, plazo, dev, tipo="vida_cash"
                )
                if df_evol.empty:
                    st.write("Sin datos.")
                else:
                    st.dataframe(df_evol, use_container_width=True, hide_index=True)

# ── Tab 8 — Insights detallados ────────────────────────────────────────────────
with tabs[7]:
    st.header("Insights del mes — detalle")

    if not insights:
        st.success("No se detectaron alertas para el último mes disponible.")
    else:
        st.caption(
            "Generados automáticamente con reglas sobre los datos cargados. "
            "Sin LLM, sin datos externos."
        )
        for ins in insights:
            color_map = {"rojo": "error", "amarillo": "warning", "verde": "success"}
            fn = getattr(st, color_map.get(ins["tipo"], "info"))
            fn(ins["texto"])

    with st.expander("Ver umbrales usados"):
        st.markdown(
            """
| Regla | Umbral |
|---|---|
| Caída de CVR (alerta roja) | Δ CVR < -15% vs mes anterior |
| Combinación crítica perdedora | Δ PxQ % < -50% **y** PxQ PRE mensual > S/1,000 |
| Caída de fuente de leads (amarillo) | Vol actual < 50% del anterior, mín. 50 leads en mes anterior |
| Calidad leads cayendo (amarillo) | % Alto cayendo ≥ 2 meses consecutivos |
| Resiliencia 125% dev (verde) | \|Δ medio 125%\| < 15% y Δ medio otros < -15% |
"""
        )
