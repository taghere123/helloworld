import { createContext, useContext, useMemo, useState } from 'react'
import { APORTE_MIN, ANIOS_MIN, calcularPlan } from '../lib/calculadora'

// Estado compartido del plan elegido por el usuario a través de las 3 pantallas.
const PlanContext = createContext(null)

export function PlanProvider({ children }) {
  const [aporteMensual, setAporteMensual] = useState(APORTE_MIN)
  const [anios, setAnios] = useState(ANIOS_MIN)
  const [frecuenciaCobro, setFrecuenciaCobro] = useState('mensual')

  const resultado = useMemo(() => calcularPlan(aporteMensual, anios), [aporteMensual, anios])

  const value = {
    aporteMensual,
    setAporteMensual,
    anios,
    setAnios,
    frecuenciaCobro,
    setFrecuenciaCobro,
    resultado,
  }

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>
}

export function usePlan() {
  const ctx = useContext(PlanContext)
  if (!ctx) throw new Error('usePlan debe usarse dentro de <PlanProvider>')
  return ctx
}
