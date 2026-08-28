// Lógica de cotización SIMULADA para el prototipo "Ahorro Plus con Sepelio".
// TODO: reemplazar calcularPlan() por la lógica actuarial real del producto
// cuando esté disponible (tasas técnicas, tablas de mortalidad, gastos, etc).

export const APORTE_MIN = 260
export const APORTE_MAX = 1200
export const APORTE_PASO = 10

export const ANIOS_MIN = 4
export const ANIOS_MAX = 15

// Beneficio de sepelio: monto FIJO, no es variable de cotización.
export const SEPELIO_MONTO = 10000

// Rango de tasa anual simulada: a mayor plazo, mayor devolución relativa
// (incentiva la permanencia, igual que en productos de ahorro con devolución).
const TASA_ANUAL_MIN = 0.035 // a ANIOS_MIN
const TASA_ANUAL_MAX = 0.055 // a ANIOS_MAX

function tasaAnualSimulada(anios) {
  const t = (anios - ANIOS_MIN) / (ANIOS_MAX - ANIOS_MIN)
  return TASA_ANUAL_MIN + t * (TASA_ANUAL_MAX - TASA_ANUAL_MIN)
}

/**
 * Calcula el resultado de la cotización a partir del aporte mensual y el
 * plazo en años. Función pura: mismos parámetros, mismo resultado.
 */
export function calcularPlan(aporteMensual, anios) {
  const meses = anios * 12
  const tasaMensual = tasaAnualSimulada(anios) / 12

  const aporteTotal = aporteMensual * meses

  // Valor futuro de una anualidad ordinaria (aportes al final de cada mes).
  const devolucionTotal =
    tasaMensual === 0
      ? aporteTotal
      : aporteMensual * ((Math.pow(1 + tasaMensual, meses) - 1) / tasaMensual)

  const ganancia = devolucionTotal - aporteTotal
  const porcentajeDevolucion = aporteTotal > 0 ? (devolucionTotal / aporteTotal) * 100 : 0

  return {
    aporteTotal: Math.round(aporteTotal),
    ganancia: Math.round(ganancia),
    devolucionTotal: Math.round(devolucionTotal),
    porcentajeDevolucion: Math.round(porcentajeDevolucion * 10) / 10,
  }
}

export function formatMonto(valor) {
  return new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 }).format(valor)
}
