from __future__ import annotations

import pandas as pd
from modules.data_loader import dias_transcurridos

MESES_PRE = [1, 2, 3]
MESES_POST = [4, 5, 6]


def _total_dias(
    df_ventas: pd.DataFrame,
    df_leads: pd.DataFrame,
    meses: list[int],
) -> int:
    return sum(dias_transcurridos(df_ventas, m, df_leads) for m in meses)


def tabla_combinaciones(
    df_ventas: pd.DataFrame,
    df_leads: pd.DataFrame,
    tipo: str | None = "vida_cash",
) -> pd.DataFrame:
    """
    Cruce Periodo de Pago × % Dev. normalizado por días.

    Returns one row per combination with PRE/POST volumes, PxQ, prima media,
    delta PxQ and delta PxQ %.  Sorted ascending by delta_pxq (worst first).
    """
    ventas = df_ventas if tipo is None else df_ventas[df_ventas["tipo_canal"] == tipo]

    ventas_pre = ventas[ventas["Mes venta"].isin(MESES_PRE)]
    ventas_post = ventas[ventas["Mes venta"].isin(MESES_POST)]

    dias_pre = _total_dias(df_ventas, df_leads, MESES_PRE)
    dias_post = _total_dias(df_ventas, df_leads, MESES_POST)

    key_cols = ["Periodo de Pago", "% Dev."]

    def _agg(df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby(key_cols)
            .agg(
                volumen=("Póliza", "count"),
                pxq=("Prima_Anual", "sum"),
                prima_media=("Prima_Anual", "mean"),
            )
            .reset_index()
        )

    pre = _agg(ventas_pre).rename(
        columns={"volumen": "vol_pre", "pxq": "pxq_pre", "prima_media": "prima_pre"}
    )
    post = _agg(ventas_post).rename(
        columns={"volumen": "vol_post", "pxq": "pxq_post", "prima_media": "prima_post"}
    )

    df = pre.merge(post, on=key_cols, how="outer").fillna(0)

    df["vol_pre_dia"] = df["vol_pre"] / dias_pre if dias_pre else 0.0
    df["vol_post_dia"] = df["vol_post"] / dias_post if dias_post else 0.0
    df["pxq_pre_dia"] = df["pxq_pre"] / dias_pre if dias_pre else 0.0
    df["pxq_post_dia"] = df["pxq_post"] / dias_post if dias_post else 0.0
    df["prima_pre"] = df["prima_pre"].round(0)
    df["prima_post"] = df["prima_post"].round(0)

    df["delta_pxq"] = df["pxq_post_dia"] - df["pxq_pre_dia"]
    df["delta_pxq_pct"] = df.apply(
        lambda r: (r["delta_pxq"] / r["pxq_pre_dia"] * 100)
        if r["pxq_pre_dia"] != 0
        else None,
        axis=1,
    )

    df = df.sort_values("delta_pxq").reset_index(drop=True)
    return df


def top_perdedoras(df_comb: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    return df_comb.head(n).copy()


def top_ganadoras(df_comb: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return df_comb.tail(n).sort_values("delta_pxq", ascending=False).copy()


def combinaciones_criticas(df_comb: pd.DataFrame, n_top: int = 5, n_bottom: int = 3) -> pd.DataFrame:
    """Return the N most impactful combinations (perdedoras + ganadoras) for Tab 7."""
    perdedoras = df_comb.head(n_top)
    ganadoras = df_comb.tail(n_bottom)
    return pd.concat([perdedoras, ganadoras]).drop_duplicates(
        subset=["Periodo de Pago", "% Dev."]
    )


def tabla_evolucion_combinacion(
    df_ventas: pd.DataFrame,
    df_leads: pd.DataFrame,
    plazo: float,
    dev: float,
    tipo: str = "vida_cash",
) -> pd.DataFrame:
    """
    Monthly evolution for a single (Periodo de Pago, % Dev.) combination.

    Columns: Mes, Ventas, CVR (ventas combo / leads VC del mes), % Part. ventas VC
    """
    ventas_vc = df_ventas[df_ventas["tipo_canal"] == tipo]
    ventas_combo = ventas_vc[
        (ventas_vc["Periodo de Pago"] == plazo) & (ventas_vc["% Dev."] == dev)
    ]

    leads_vc = df_leads[df_leads["tipo_canal"] == tipo]
    leads_mes = leads_vc.groupby("Mes").size().rename("leads_vc")
    ventas_vc_mes = ventas_vc.groupby("Mes venta").size().rename("ventas_vc")
    ventas_combo_mes = ventas_combo.groupby("Mes venta").size().rename("ventas_combo")

    meses = sorted(
        set(leads_mes.index) | set(ventas_vc_mes.index) | set(ventas_combo_mes.index)
    )
    rows = []
    for mes in meses:
        vc = int(ventas_combo_mes.get(mes, 0))
        lvc = int(leads_mes.get(mes, 0))
        vvc = int(ventas_vc_mes.get(mes, 0))
        cvr = vc / lvc * 100 if lvc else 0.0
        part = vc / vvc * 100 if vvc else 0.0
        rows.append(
            {
                "Mes": mes,
                "Ventas combo": vc,
                "CVR combo/leads VC (%)": round(cvr, 3),
                "% Part. ventas VC": round(part, 1),
            }
        )
    return pd.DataFrame(rows)
