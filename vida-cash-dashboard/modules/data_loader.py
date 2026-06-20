from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

CANALES_VIDA_CASH = [
    "VIDA_CASH_DEVOLUCION",
    "VIDA_CASH_PLUS",
    "VIDA_CASH_PLUS_IBK_SELECT",
    "WEB",
]
CANALES_ENDOSOS = [
    "ENDOSOS",
    "ENDOSOS_IBK",
    "ENDOSO_CON_DEVOLUCION_IBK_SELECT",
    "ENDOSO_CON_DEVOLUCIÓN_IBK_SELECT",
]
TODOS_CANALES = CANALES_VIDA_CASH + CANALES_ENDOSOS

# Static days per month for months 1-5; month 6+ derived dynamically
DIAS_ESTATICOS: dict[int, int] = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31}


def get_file_mtimes() -> tuple[float | None, float | None]:
    leads_p = DATA_DIR / "Leads.xlsx"
    ventas_p = DATA_DIR / "Ventas.xlsx"
    return (
        leads_p.stat().st_mtime if leads_p.exists() else None,
        ventas_p.stat().st_mtime if ventas_p.exists() else None,
    )


def dias_transcurridos(
    df_ventas: pd.DataFrame,
    mes: int,
    df_leads: pd.DataFrame | None = None,
) -> int:
    """
    Return the number of days of data available for `mes`.

    For months in DIAS_ESTATICOS the static value is used.  For any other
    month (e.g. the current cut-off month) the value is derived from the
    maximum day found in the raw data, so the dashboard scales automatically
    as the user replaces the source files.
    """
    if mes in DIAS_ESTATICOS:
        return DIAS_ESTATICOS[mes]

    # Prefer Leads.Dia (explicitly documented integer day-of-month column)
    if df_leads is not None and "Dia" in df_leads.columns:
        sub = df_leads[df_leads["Mes"] == mes]["Dia"]
        if not sub.empty:
            val = pd.to_numeric(sub, errors="coerce").max()
            if pd.notna(val) and val > 0:
                return int(val)

    # Fall back to parsing F. venta date column in ventas (unreliable for ~800 rows
    # but good enough to find the max day)
    if "F. venta" in df_ventas.columns:
        sub = df_ventas[df_ventas["Mes venta"] == mes]["F. venta"]
        fechas = pd.to_datetime(sub, errors="coerce")
        val = fechas.dt.day.max()
        if pd.notna(val) and val > 0:
            return int(val)

    # Hard-coded fallbacks for standard months
    fallback = {6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    return fallback.get(mes, 30)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    """
    Load and validate Leads.xlsx and Ventas.xlsx.

    Returns (df_leads, df_ventas, invalid_leads_count, invalid_ventas_count).
    Rows with Mes/Mes venta outside 1-12 or null are excluded and counted.
    """
    leads_path = DATA_DIR / "Leads.xlsx"
    ventas_path = DATA_DIR / "Ventas.xlsx"

    # ── Leads ──────────────────────────────────────────────────────────────────
    raw_leads = pd.read_excel(leads_path, engine="openpyxl")
    raw_leads["Mes"] = pd.to_numeric(raw_leads["Mes"], errors="coerce")
    mask_valid_leads = raw_leads["Mes"].notna() & raw_leads["Mes"].between(1, 12)
    invalid_leads_count = int((~mask_valid_leads).sum())

    df_leads = raw_leads[mask_valid_leads].copy()
    df_leads["Mes"] = df_leads["Mes"].astype(int)

    # Keep only known canales
    df_leads = df_leads[df_leads["Canal"].isin(TODOS_CANALES)].copy()
    df_leads["tipo_canal"] = df_leads["Canal"].map(
        lambda c: "vida_cash" if c in CANALES_VIDA_CASH else "endosos"
    )

    # ── Ventas ─────────────────────────────────────────────────────────────────
    raw_ventas = pd.read_excel(ventas_path, engine="openpyxl")
    raw_ventas["Mes venta"] = pd.to_numeric(raw_ventas["Mes venta"], errors="coerce")
    mask_valid_ventas = (
        raw_ventas["Mes venta"].notna() & raw_ventas["Mes venta"].between(1, 12)
    )
    invalid_ventas_count = int((~mask_valid_ventas).sum())

    df_ventas = raw_ventas[mask_valid_ventas].copy()
    df_ventas["Mes venta"] = df_ventas["Mes venta"].astype(int)

    # Include ALL estados (VIGENTE/CANCELADA/CADUCADA) — no filter
    df_ventas = df_ventas[df_ventas["Canal"].isin(TODOS_CANALES)].copy()
    df_ventas["tipo_canal"] = df_ventas["Canal"].map(
        lambda c: "vida_cash" if c in CANALES_VIDA_CASH else "endosos"
    )

    # Prima anual — always recalculate, never trust a pre-existing column
    df_ventas["Prima_Anual"] = df_ventas["Prima"] * df_ventas["Frecuencia"]

    return df_leads, df_ventas, invalid_leads_count, invalid_ventas_count
