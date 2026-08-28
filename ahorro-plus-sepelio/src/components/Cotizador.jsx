import ScreenHeader from './ScreenHeader'
import { usePlan } from '../context/PlanContext'
import {
  APORTE_MIN,
  APORTE_MAX,
  APORTE_PASO,
  ANIOS_MIN,
  ANIOS_MAX,
  SEPELIO_MONTO,
  formatMonto,
} from '../lib/calculadora'

export default function Cotizador({ onBack, onConfirmar }) {
  const { aporteMensual, setAporteMensual, anios, setAnios, resultado } = usePlan()

  return (
    <div className="min-h-full flex flex-col bg-white">
      <ScreenHeader title="Cotizador" onBack={onBack} />

      <div className="px-5 py-6 flex flex-col gap-7">
        <div>
          <h1 className="text-lg font-bold text-slate-900">Arma tu plan</h1>
          <p className="text-sm text-slate-500 mt-1">
            Mueve los controles y mira cómo cambia tu devolución al instante.
          </p>
        </div>

        {/* Slider: aporte mensual */}
        <div>
          <div className="flex items-baseline justify-between mb-2">
            <label htmlFor="aporte" className="text-sm font-semibold text-slate-700">
              ¿Cuánto deseas ahorrar al mes?
            </label>
          </div>
          <p className="text-2xl font-extrabold text-brand">S/ {formatMonto(aporteMensual)}</p>
          <input
            id="aporte"
            type="range"
            min={APORTE_MIN}
            max={APORTE_MAX}
            step={APORTE_PASO}
            value={aporteMensual}
            onChange={(e) => setAporteMensual(Number(e.target.value))}
            className="w-full mt-3"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>S/ {formatMonto(APORTE_MIN)}</span>
            <span>S/ {formatMonto(APORTE_MAX)}</span>
          </div>
        </div>

        {/* Slider: años */}
        <div>
          <label htmlFor="anios" className="text-sm font-semibold text-slate-700">
            ¿Por cuántos años?
          </label>
          <p className="text-2xl font-extrabold text-brand mt-2">
            {anios} {anios === 1 ? 'año' : 'años'}
          </p>
          <input
            id="anios"
            type="range"
            min={ANIOS_MIN}
            max={ANIOS_MAX}
            step={1}
            value={anios}
            onChange={(e) => setAnios(Number(e.target.value))}
            className="w-full mt-3"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>{ANIOS_MIN} años</span>
            <span>{ANIOS_MAX} años</span>
          </div>
        </div>

        {/* Tarjeta de resultado */}
        <div className="rounded-[12px] border border-brand-light bg-brand-soft p-5">
          <p className="text-sm font-semibold text-slate-700 mb-2">Tu devolución estimada</p>
          <span className="inline-block bg-brand text-white text-xs font-bold px-2.5 py-1 rounded-full mb-4">
            {resultado.porcentajeDevolucion}% de tu aporte
          </span>

          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Mi aporte total</span>
              <span className="font-semibold text-slate-800">
                S/ {formatMonto(resultado.aporteTotal)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Mi ganancia</span>
              <span className="font-semibold text-slate-800">
                S/ {formatMonto(resultado.ganancia)}
              </span>
            </div>
            <div className="h-px bg-brand-light" />
            <div className="flex justify-between items-baseline">
              <span className="text-sm font-semibold text-slate-700">Devolución total</span>
              <span className="text-xl font-extrabold text-brand">
                S/ {formatMonto(resultado.devolucionTotal)}
              </span>
            </div>
          </div>
        </div>

        {/* Nota fija de sepelio */}
        <div className="flex items-start gap-2 rounded-[12px] bg-slate-50 border border-slate-100 p-3.5">
          <span className="text-lg leading-none">🕊️</span>
          <p className="text-xs text-slate-500">
            Tu plan incluye, sin costo adicional, un seguro de sepelio por{' '}
            <span className="font-semibold text-slate-700">
              S/ {formatMonto(SEPELIO_MONTO)}
            </span>
            .
          </p>
        </div>

        <button
          onClick={onConfirmar}
          className="w-full bg-brand text-white font-semibold py-3.5 rounded-[12px] active:opacity-90"
        >
          Confirmar plan
        </button>
      </div>
    </div>
  )
}
