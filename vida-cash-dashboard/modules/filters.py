from __future__ import annotations

import pandas as pd

DIAS_SEMANA_ES: dict[int, str] = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}

MESES_ES: dict[int, str] = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# Fuente Anuncio → Canal macro. Override with a "Canal" column in the data if present.
FUENTE_A_CANAL_MACRO: dict[str, str] = {
    "google": "Paid Media",
    "facebook": "Paid Media",
    "tiktok": "Paid Media",
    "bing": "Paid Media",
    "interseguro": "Organic",
    "salesforce": "Organic",
    "email": "Owned Media",
    "whatsapp": "Owned Media",
    "sms": "Owned Media",
    "push": "Owned Media",
}

PERIODOS = ["Diaria", "Semanal", "Mensual", "Trimestral", "Anual"]
TIPOS_VISTA = ["Venta del mes", "Leads del mes"]


def enrich_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Add date-derived columns used by filters and periodo aggregation."""
    df = df.copy()
    if "FechaAsignacion" in df.columns:
        df["fecha_lead"] = pd.to_datetime(df["FechaAsignacion"], errors="coerce")
        df["dia_semana_lead"] = df["fecha_lead"].dt.dayofweek
        # Prefer parsed date day; fall back to explicit Dia column
        df["dia_mes_lead"] = df["fecha_lead"].dt.day
        if "Dia" in df.columns:
            mask_null = df["dia_mes_lead"].isna()
            df.loc[mask_null, "dia_mes_lead"] = pd.to_numeric(
                df.loc[mask_null, "Dia"], errors="coerce"
            )
    elif "Dia" in df.columns:
        df["dia_mes_lead"] = pd.to_numeric(df["Dia"], errors="coerce")

    # Canal macro: use dedicated column if present, else derive from Fuente Anuncio
    if "Canal Macro" in df.columns:
        df["canal_macro"] = df["Canal Macro"]
    elif "Fuente Anuncio" in df.columns:
        norm = df["Fuente Anuncio"].str.lower().str.strip()
        df["canal_macro"] = norm.map(FUENTE_A_CANAL_MACRO).fillna("Otro")

    return df


def enrich_ventas(df: pd.DataFrame) -> pd.DataFrame:
    """Add date-derived columns to df_ventas."""
    df = df.copy()
    if "F. venta" in df.columns:
        df["fecha_venta"] = pd.to_datetime(df["F. venta"], errors="coerce")
        df["dia_semana_venta"] = df["fecha_venta"].dt.dayofweek
        df["dia_mes_venta"] = df["fecha_venta"].dt.day
    return df


def periodo_key(df: pd.DataFrame, date_col: str, mes_col: str, periodo: str) -> pd.Series:
    """
    Return a Series of grouping keys for the given periodo.

    Falls back to month-based keys when date column is missing or has nulls.
    """
    has_date = date_col in df.columns and df[date_col].notna().any()

    if periodo == "Diaria":
        if has_date:
            return df[date_col].dt.strftime("%Y-%m-%d")
        return df[mes_col].astype(str).str.zfill(2).rename("periodo")

    if periodo == "Semanal":
        if has_date:
            return df[date_col].dt.strftime("%G-W%V")
        return df[mes_col].astype(str).str.zfill(2).rename("periodo")

    if periodo == "Mensual":
        if has_date:
            return df[date_col].dt.strftime("%Y-%m").where(
                df[date_col].notna(),
                "2026-" + df[mes_col].astype(str).str.zfill(2),
            )
        return ("2026-" + df[mes_col].astype(str).str.zfill(2)).rename("periodo")

    if periodo == "Trimestral":
        mes = df[mes_col] if mes_col in df.columns else df[date_col].dt.month
        return mes.map(lambda m: f"Q{(int(m) - 1) // 3 + 1}" if pd.notna(m) else None)

    if periodo == "Anual":
        if has_date:
            return df[date_col].dt.year.astype(str)
        return pd.Series(["2026"] * len(df), index=df.index)

    return df[mes_col].astype(str)


def apply_filters(
    df_leads: pd.DataFrame,
    df_ventas: pd.DataFrame,
    *,
    fecha_inicio=None,
    fecha_fin=None,
    dias_semana: list[str] | None = None,
    dias_mes: list[int] | None = None,
    meses: list[str] | None = None,
    sub_producto: list[str] | None = None,
    canal: list[str] | None = None,
    sub_canal: list[str] | None = None,
    sub_sub_canal: list[str] | None = None,
    call_center: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply all active filters. Empty list = no filter applied for that dimension."""
    df_l = df_leads.copy()
    df_v = df_ventas.copy()

    # Sub producto
    if sub_producto:
        tipo_map = {"Vida Cash": "vida_cash", "Endosos": "endosos"}
        tipos = [tipo_map[s] for s in sub_producto if s in tipo_map]
        if tipos:
            df_l = df_l[df_l["tipo_canal"].isin(tipos)]
            df_v = df_v[df_v["tipo_canal"].isin(tipos)]

    # Mes
    if meses:
        inv = {v: k for k, v in MESES_ES.items()}
        nums = [inv[m] for m in meses if m in inv]
        if nums:
            df_l = df_l[df_l["Mes"].isin(nums)]
            df_v = df_v[df_v["Mes venta"].isin(nums)]

    # Día del mes (leads)
    if dias_mes and "dia_mes_lead" in df_l.columns:
        df_l = df_l[df_l["dia_mes_lead"].isin(dias_mes)]
    if dias_mes and "dia_mes_venta" in df_v.columns:
        # Keep rows without date (don't exclude them, just can't verify)
        mask = df_v["dia_mes_venta"].isna() | df_v["dia_mes_venta"].isin(dias_mes)
        df_v = df_v[mask]

    # Día de semana
    if dias_semana:
        inv_ds = {v: k for k, v in DIAS_SEMANA_ES.items()}
        nums_ds = [inv_ds[d] for d in dias_semana if d in inv_ds]
        if nums_ds:
            if "dia_semana_lead" in df_l.columns:
                df_l = df_l[df_l["dia_semana_lead"].isin(nums_ds)]
            if "dia_semana_venta" in df_v.columns:
                mask = df_v["dia_semana_venta"].isna() | df_v["dia_semana_venta"].isin(nums_ds)
                df_v = df_v[mask]

    # Fecha inicio / fin
    if fecha_inicio is not None and "fecha_lead" in df_l.columns:
        mask = df_l["fecha_lead"].isna() | (df_l["fecha_lead"].dt.date >= fecha_inicio)
        df_l = df_l[mask]
    if fecha_fin is not None and "fecha_lead" in df_l.columns:
        mask = df_l["fecha_lead"].isna() | (df_l["fecha_lead"].dt.date <= fecha_fin)
        df_l = df_l[mask]
    if fecha_inicio is not None and "fecha_venta" in df_v.columns:
        mask = df_v["fecha_venta"].isna() | (df_v["fecha_venta"].dt.date >= fecha_inicio)
        df_v = df_v[mask]
    if fecha_fin is not None and "fecha_venta" in df_v.columns:
        mask = df_v["fecha_venta"].isna() | (df_v["fecha_venta"].dt.date <= fecha_fin)
        df_v = df_v[mask]

    # Canal macro (Organic / Paid Media / Owned Media)
    if canal and "canal_macro" in df_l.columns:
        df_l = df_l[df_l["canal_macro"].isin(canal)]

    # Sub canal (Fuente Anuncio)
    if sub_canal and "Fuente Anuncio" in df_l.columns:
        norm_sc = [s.lower().strip() for s in sub_canal]
        df_l = df_l[df_l["Fuente Anuncio"].str.lower().str.strip().isin(norm_sc)]

    # Sub sub canal
    if sub_sub_canal:
        for col in ("Sub Canal", "SubCanal", "sub_sub_canal", "Sub Sub Canal"):
            if col in df_l.columns:
                df_l = df_l[df_l[col].isin(sub_sub_canal)]
                break

    # Call center
    if call_center:
        for col in ("Call Center", "CallCenter", "call_center", "Centro Llamadas"):
            if col in df_l.columns:
                df_l = df_l[df_l[col].isin(call_center)]
                break
            if col in df_v.columns:
                df_v = df_v[df_v[col].isin(call_center)]
                break

    return df_l, df_v


def _unique_vals(df: pd.DataFrame, col: str) -> list[str]:
    """Return sorted unique non-null string values for a column."""
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())
