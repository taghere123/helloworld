from __future__ import annotations

import pandas as pd

from modules.data_loader import dias_transcurridos
from modules.filters import MESES_ES, periodo_key


def _leads_por_periodo(
    df_leads: pd.DataFrame,
    periodo: str,
) -> pd.Series:
    """Lead counts indexed by periodo key."""
    keys = periodo_key(df_leads, "fecha_lead", "Mes", periodo)
    return df_leads.groupby(keys).size().rename("leads")


def _ventas_por_periodo(
    df_ventas: pd.DataFrame,
    periodo: str,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Ventas count, PxQ sum, and Prima media indexed by periodo key."""
    keys = periodo_key(df_ventas, "fecha_venta", "Mes venta", periodo)
    grp = df_ventas.groupby(keys)
    return (
        grp.size().rename("polizas"),
        grp["Prima_Anual"].sum().rename("pxq"),
        grp["Prima_Anual"].mean().rename("prima_media"),
    )


def _dias_por_periodo_key(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
    periodo: str,
) -> dict[str, int]:
    """
    Approximate days in each periodo key for normalization.

    For Mensual: uses dias_transcurridos.
    For other periodos: uses the distinct date count when dates are available,
    otherwise falls back to 30.
    """
    if periodo == "Mensual":
        meses = sorted(
            set(df_leads["Mes"].unique()) | set(df_ventas["Mes venta"].unique())
        )
        keys = periodo_key(
            pd.DataFrame({"Mes": meses}), "fecha_lead", "Mes", "Mensual"
        )
        return {k: dias_transcurridos(df_ventas, m, df_leads) for k, m in zip(keys, meses)}

    if periodo == "Trimestral":
        q_days = {"Q1": 90, "Q2": 91, "Q3": 92, "Q4": 92}
        return {q: q_days.get(q, 91) for q in q_days}

    if periodo == "Anual":
        return {"2026": 365}

    # Diaria: 1 day per key; Semanal: 7 days per key
    day_count = {"Diaria": 1, "Semanal": 7}
    default = day_count.get(periodo, 30)
    all_keys = set()
    if "fecha_lead" in df_leads.columns:
        all_keys |= set(periodo_key(df_leads, "fecha_lead", "Mes", periodo).dropna().unique())
    if "fecha_venta" in df_ventas.columns:
        all_keys |= set(periodo_key(df_ventas, "fecha_venta", "Mes venta", periodo).dropna().unique())
    return {k: default for k in all_keys}


def tabla_funnel(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
    tipo: str | None = None,
    periodo: str = "Mensual",
    tipo_vista: str = "Venta del mes",
) -> pd.DataFrame:
    """
    Build funnel table at the requested periodo granularity.

    tipo_vista:
      'Venta del mes'  — standard calendar: ventas del periodo / leads del periodo.
      'Leads del mes'  — cohort: for each periodo, ventas attributable to leads
                         that entered in that same periodo (join by document).
    """
    leads = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    ventas = df_ventas if tipo is None else df_ventas[df_ventas["tipo_canal"] == tipo]

    if tipo_vista == "Leads del mes":
        # Join ventas to their matching lead's periodo
        leads_doc = leads[["NumeroDocumento", "Mes"]].copy()
        ventas_doc = ventas.copy()
        ventas_doc = ventas_doc.rename(columns={"N° de doc.": "NumeroDocumento"})
        merged = ventas_doc.merge(leads_doc, on="NumeroDocumento", how="inner")
        merged = merged[merged["Mes venta"] >= merged["Mes"]]
        merged = merged.sort_values("Mes venta").drop_duplicates(subset=["Póliza"])
        # Group ventas by the LEAD's periodo
        ventas_for_periodo = merged.rename(columns={"Mes": "Mes venta"})
        n_polizas_s, pxq_s, prima_s = _ventas_por_periodo(ventas_for_periodo, periodo)
    else:
        n_polizas_s, pxq_s, prima_s = _ventas_por_periodo(ventas, periodo)

    n_leads_s = _leads_por_periodo(leads, periodo)
    dias_map = _dias_por_periodo_key(leads, ventas, periodo)

    all_keys = sorted(set(n_leads_s.index) | set(n_polizas_s.index))

    rows = []
    cvr_prev: float | None = None
    for key in all_keys:
        n_leads = int(n_leads_s.get(key, 0))
        n_polizas = int(n_polizas_s.get(key, 0))
        dias = dias_map.get(key, 30)
        leads_dia = n_leads / dias if dias else 0.0
        polizas_dia = n_polizas / dias if dias else 0.0
        cvr = n_polizas / n_leads if n_leads else 0.0
        delta_cvr = (cvr - cvr_prev) / cvr_prev * 100 if cvr_prev else None
        pxq_total = float(pxq_s.get(key, 0))
        pxq_dia = pxq_total / dias if dias else 0.0
        prima_media = float(prima_s.get(key, 0))

        rows.append(
            {
                "Periodo": key,
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
    df = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    if df.empty or "TipoLead" not in df.columns:
        return pd.DataFrame()
    pivot = df.groupby(["Mes", "TipoLead"]).size().unstack(fill_value=0)
    return (pivot.div(pivot.sum(axis=1), axis=0) * 100).round(1)


_FUENTES = ["google", "facebook", "tiktok", "bing", "interseguro", "salesforce"]


def tabla_fuente_leads(
    df_leads: pd.DataFrame,
    tipo: str | None = None,
) -> pd.DataFrame:
    df = df_leads if tipo is None else df_leads[df_leads["tipo_canal"] == tipo]
    if df.empty or "Fuente Anuncio" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["fuente_norm"] = tmp["Fuente Anuncio"].str.lower().str.strip()
    pivot = tmp.groupby(["Mes", "fuente_norm"]).size().unstack(fill_value=0)
    for f in _FUENTES:
        if f not in pivot.columns:
            pivot[f] = 0
    cols = [f for f in _FUENTES if f in pivot.columns]
    return pivot[cols]


def tabla_comparativo_cvr(
    df_vc: pd.DataFrame, df_end: pd.DataFrame, df_tot: pd.DataFrame
) -> pd.DataFrame:
    base = df_tot[["Periodo"]].copy().set_index("Periodo")

    def _get(df: pd.DataFrame) -> pd.Series:
        return df.set_index("Periodo")["CVR (%)"]

    base["CVR Vida Cash (%)"] = _get(df_vc)
    base["CVR Endosos (%)"] = _get(df_end)
    base["CVR Total (%)"] = _get(df_tot)
    base["Spread VC-End (pp)"] = (
        base["CVR Vida Cash (%)"] - base["CVR Endosos (%)"]
    ).round(2)
    return base.reset_index()


def tabla_comparativo_pxq(
    df_vc: pd.DataFrame, df_end: pd.DataFrame, df_tot: pd.DataFrame
) -> pd.DataFrame:
    base = df_tot[["Periodo"]].copy().set_index("Periodo")

    def _get(df: pd.DataFrame) -> pd.Series:
        return df.set_index("Periodo")["PxQ/día (S/)"]

    base["PxQ/día Vida Cash"] = _get(df_vc)
    base["PxQ/día Endosos"] = _get(df_end)
    base["PxQ/día Total"] = _get(df_tot)
    base["% Part. Endosos"] = (
        base["PxQ/día Endosos"] / base["PxQ/día Total"] * 100
    ).round(1)
    return base.reset_index()
