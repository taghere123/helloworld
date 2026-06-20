from __future__ import annotations

import pandas as pd


def generar_insights(
    df_funnel_vc: pd.DataFrame,
    df_funnel_end: pd.DataFrame,
    df_funnel_total: pd.DataFrame,
    df_comb: pd.DataFrame,
    df_leads: pd.DataFrame,
    umbral_pxq_mensual: float = 1_000,
) -> list[dict]:
    """
    Generate rule-based insights for the latest month available.

    Returns a list of {tipo: 'rojo'|'amarillo'|'verde', texto: str} sorted
    red → yellow → green.
    """
    insights: list[dict] = []

    if df_funnel_total.empty:
        return insights

    mes_actual = int(df_funnel_total["Mes"].max())

    # ── CVR drop rule ──────────────────────────────────────────────────────────
    def _cvr_check(df: pd.DataFrame, canal: str) -> None:
        if len(df) < 2:
            return
        row = df[df["Mes"] == mes_actual]
        if row.empty:
            return
        delta = row.iloc[0]["ΔCVR (%)"]
        cvr_actual = row.iloc[0]["CVR (%)"]
        if delta is None or pd.isna(delta):
            return
        mes_prev = mes_actual - 1
        row_prev = df[df["Mes"] == mes_prev]
        if row_prev.empty:
            return
        cvr_anterior = row_prev.iloc[0]["CVR (%)"]
        if delta < -15:
            es_min = cvr_actual <= df["CVR (%)"].min()
            txt = (
                f"⚠️ El CVR de {canal} cayó {abs(delta):.1f}% vs el mes anterior "
                f"({cvr_anterior:.2f}% → {cvr_actual:.2f}%)."
            )
            if es_min:
                txt += " Es el nivel más bajo del año."
            insights.append({"tipo": "rojo", "texto": txt})

    _cvr_check(df_funnel_vc, "Vida Cash")
    _cvr_check(df_funnel_end, "Endosos")
    _cvr_check(df_funnel_total, "Total")

    # ── Combinaciones perdedoras críticas ──────────────────────────────────────
    for _, row in df_comb.iterrows():
        pct = row.get("delta_pxq_pct")
        pxq_pre_mensual = row["pxq_pre_dia"] * 30
        if pd.notna(pct) and pct < -50 and pxq_pre_mensual > umbral_pxq_mensual:
            plazo = row["Periodo de Pago"]
            dev = row["% Dev."]
            pxq_pre = row["pxq_pre_dia"] * 30
            pxq_post = row["pxq_post_dia"] * 30
            delta_abs = abs(pxq_post - pxq_pre)
            insights.append(
                {
                    "tipo": "rojo",
                    "texto": (
                        f"🔴 La combinación {plazo}a / {dev}% perdió {abs(pct):.0f}% de su "
                        f"PxQ mensual (S/{pxq_pre:,.0f} → S/{pxq_post:,.0f}), "
                        f"una pérdida de S/{delta_abs:,.0f}/mes."
                    ),
                }
            )

    # ── Caída de fuentes de leads > 50% ───────────────────────────────────────
    if "Fuente Anuncio" in df_leads.columns:
        tmp = df_leads.copy()
        tmp["fuente_norm"] = tmp["Fuente Anuncio"].str.lower().str.strip()
        fuente_mes = tmp.groupby(["Mes", "fuente_norm"]).size().unstack(fill_value=0)
        mes_prev = mes_actual - 1
        if mes_actual in fuente_mes.index and mes_prev in fuente_mes.index:
            for fuente in fuente_mes.columns:
                vol_ant = int(fuente_mes.loc[mes_prev, fuente])
                vol_act = int(fuente_mes.loc[mes_actual, fuente])
                if vol_ant > 50 and vol_act < vol_ant * 0.5:
                    insights.append(
                        {
                            "tipo": "amarillo",
                            "texto": (
                                f"⚠️ La fuente {fuente} cayó de {vol_ant:,} a "
                                f"{vol_act:,} leads — revisar con equipo de paid media."
                            ),
                        }
                    )

    # ── Calidad de leads (% Alto) cayendo ≥ 2 meses consecutivos ──────────────
    if "TipoLead" in df_leads.columns:
        cal = df_leads.groupby(["Mes", "TipoLead"]).size().unstack(fill_value=0)
        if "Alto" in cal.columns:
            total = cal.sum(axis=1)
            pct_alto = (cal["Alto"] / total * 100).sort_index()
            meses_ord = sorted(pct_alto.index)
            streak = 0
            for i in range(1, len(meses_ord)):
                if pct_alto[meses_ord[i]] < pct_alto[meses_ord[i - 1]]:
                    streak += 1
                else:
                    streak = 0
            if streak >= 2:
                insights.append(
                    {
                        "tipo": "amarillo",
                        "texto": (
                            f"📉 La calidad de leads (% Alto) viene cayendo "
                            f"por {streak} meses consecutivos."
                        ),
                    }
                )

    # ── Resiliencia de combinaciones 125% dev ──────────────────────────────────
    comb_125 = df_comb[df_comb["% Dev."] == 125]
    comb_otros = df_comb[df_comb["% Dev."] != 125]
    if not comb_125.empty and not comb_otros.empty:
        med_125 = comb_125["delta_pxq_pct"].mean()
        med_otros = comb_otros["delta_pxq_pct"].mean()
        if pd.notna(med_125) and pd.notna(med_otros) and abs(med_125) < 15 and med_otros < -15:
            insights.append(
                {
                    "tipo": "verde",
                    "texto": (
                        "✅ Las combinaciones con 125% de devolución muestran resiliencia "
                        "relativa — posible patrón de sustitución del cliente hacia el "
                        "plan más económico."
                    ),
                }
            )

    # ── Sort: rojo → amarillo → verde ─────────────────────────────────────────
    orden = {"rojo": 0, "amarillo": 1, "verde": 2}
    insights.sort(key=lambda x: orden.get(x["tipo"], 9))
    return insights
