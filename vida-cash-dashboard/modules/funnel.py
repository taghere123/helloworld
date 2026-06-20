from __future__ import annotations

import pandas as pd
from modules.data_loader import dias_transcurridos


def tabla_funnel(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
    tipo: str | None = None,
) -> pd.DataFrame:
    """
    Build monthly funnel table.

    tipo: None = all canales, 'vida_cash', 'endosos'
    Columns: Mes, Leads, Leads/día, Pólizas, Pólizas/día, CVR, ΔCVR, PxQ/día, Prima media
    """
    leads = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    ventas = df_ventas if tipo is None else df_ventas[df_ventas["tipo_canal"] == tipo]

    meses = sorted(set(leads["Mes"].unique()) | set(ventas["Mes venta"].unique()))

    rows = []
    cvr_prev: float | None = None

    for mes in meses:
        n_leads = int((leads["Mes"] == mes).sum())
        ventas_mes = ventas[ventas["Mes venta"] == mes]
        n_polizas = len(ventas_mes)
        dias = dias_transcurridos(df_ventas, mes, df_leads)

        leads_dia = n_leads / dias if dias else 0.0
        polizas_dia = n_polizas / dias if dias else 0.0
        cvr = n_polizas / n_leads if n_leads else 0.0

        if cvr_prev is not None and cvr_prev > 0:
            delta_cvr: float | None = (cvr - cvr_prev) / cvr_prev * 100
        else:
            delta_cvr = None

        pxq_total = ventas_mes["Prima_Anual"].sum()
        pxq_dia = pxq_total / dias if dias else 0.0
        prima_media = ventas_mes["Prima_Anual"].mean() if n_polizas else 0.0

        rows.append(
            {
                "Mes": mes,
                "Leads": n_leads,
                "Leads/día": round(leads_dia, 1),
                "Pólizas": n_polizas,
                "Pólizas/día": round(polizas_dia, 2),
                "CVR (%)": round(cvr * 100, 2),
                "ΔCVR (%)": round(delta_cvr, 2) if delta_cvr is not None else None,
                "PxQ/día (S/)": round(pxq_dia, 0),
                "Prima media (S/)": round(prima_media, 0),
            }
        )
        cvr_prev = cvr

    return pd.DataFrame(rows)


def tabla_calidad_leads(
    df_leads: pd.DataFrame,
    tipo: str | None = None,
) -> pd.DataFrame:
    """Lead quality distribution (% per TipoLead) by month."""
    df = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    if df.empty or "TipoLead" not in df.columns:
        return pd.DataFrame()
    pivot = df.groupby(["Mes", "TipoLead"]).size().unstack(fill_value=0)
    pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
    return pct.round(1)


_FUENTES_CONOCIDAS = ["google", "facebook", "tiktok", "bing", "interseguro", "salesforce"]


def tabla_fuente_leads(
    df_leads: pd.DataFrame,
    tipo: str | None = None,
) -> pd.DataFrame:
    """Lead volume by source per month. Columns: google, facebook, tiktok, bing, interseguro."""
    df = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    if df.empty or "Fuente Anuncio" not in df.columns:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["fuente_norm"] = tmp["Fuente Anuncio"].str.lower().str.strip()
    pivot = tmp.groupby(["Mes", "fuente_norm"]).size().unstack(fill_value=0)

    for f in _FUENTES_CONOCIDAS:
        if f not in pivot.columns:
            pivot[f] = 0

    # Only return the known sources that actually exist in data
    cols = [f for f in _FUENTES_CONOCIDAS if f in pivot.columns]
    return pivot[cols]


def tabla_comparativo_cvr(
    df_funnel_vc: pd.DataFrame,
    df_funnel_end: pd.DataFrame,
    df_funnel_total: pd.DataFrame,
) -> pd.DataFrame:
    """CVR side-by-side for Vida Cash, Endosos, Total + spread."""
    base = df_funnel_total[["Mes"]].copy()

    def _get(df: pd.DataFrame, col: str = "CVR (%)") -> pd.Series:
        return df.set_index("Mes")[col]

    base = base.set_index("Mes")
    base["CVR Vida Cash (%)"] = _get(df_funnel_vc)
    base["CVR Endosos (%)"] = _get(df_funnel_end)
    base["CVR Total (%)"] = _get(df_funnel_total)
    base["Spread VC-End (pp)"] = (base["CVR Vida Cash (%)"] - base["CVR Endosos (%)"]).round(2)
    return base.reset_index()


def tabla_comparativo_pxq(
    df_funnel_vc: pd.DataFrame,
    df_funnel_end: pd.DataFrame,
    df_funnel_total: pd.DataFrame,
) -> pd.DataFrame:
    """PxQ/día comparison with Endosos participation %."""
    base = df_funnel_total[["Mes"]].copy().set_index("Mes")

    def _get(df: pd.DataFrame) -> pd.Series:
        return df.set_index("Mes")["PxQ/día (S/)"]

    base["PxQ/día Vida Cash"] = _get(df_funnel_vc)
    base["PxQ/día Endosos"] = _get(df_funnel_end)
    base["PxQ/día Total"] = _get(df_funnel_total)
    base["% Part. Endosos"] = (
        base["PxQ/día Endosos"] / base["PxQ/día Total"] * 100
    ).round(1)
    return base.reset_index()
