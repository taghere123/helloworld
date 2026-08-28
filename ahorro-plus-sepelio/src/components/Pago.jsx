import { useState } from 'react'
import ScreenHeader from './ScreenHeader'
import { usePlan } from '../context/PlanContext'
import { formatMonto } from '../lib/calculadora'

function formatearNumeroTarjeta(valor) {
  const digitos = valor.replace(/\D/g, '').slice(0, 16)
  return digitos.replace(/(.{4})/g, '$1 ').trim()
}

function formatearExpiracion(valor) {
  const digitos = valor.replace(/\D/g, '').slice(0, 4)
  if (digitos.length <= 2) return digitos
  return `${digitos.slice(0, 2)}/${digitos.slice(2)}`
}

export default function Pago({ onVolverInicio }) {
  const { aporteMensual, anios, resultado, frecuenciaCobro, setFrecuenciaCobro } = usePlan()

  const [numeroTarjeta, setNumeroTarjeta] = useState('')
  const [nombreTitular, setNombreTitular] = useState('')
  const [expiracion, setExpiracion] = useState('')
  const [cvv, setCvv] = useState('')
  const [aceptaPolitica, setAceptaPolitica] = useState(false)
  const [compraConfirmada, setCompraConfirmada] = useState(false)

  const formularioCompleto =
    numeroTarjeta.replace(/\s/g, '').length === 16 &&
    nombreTitular.trim().length > 2 &&
    expiracion.length === 5 &&
    cvv.length >= 3 &&
    aceptaPolitica

  return (
    <div className="min-h-full flex flex-col bg-white relative">
      <ScreenHeader title="Confirmar y pagar" />

      <div className="px-5 py-6 flex flex-col gap-6">
        {/* Resumen del plan */}
        <div className="rounded-[12px] bg-brand-soft border border-brand-light p-4">
          <p className="text-sm font-semibold text-slate-700 mb-3">Resumen de tu plan</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Aporte mensual</span>
              <span className="font-semibold text-slate-800">
                S/ {formatMonto(aporteMensual)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Plazo</span>
              <span className="font-semibold text-slate-800">
                {anios} {anios === 1 ? 'año' : 'años'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Devolución total</span>
              <span className="font-semibold text-slate-800">
                S/ {formatMonto(resultado.devolucionTotal)}
              </span>
            </div>
            <div className="flex justify-between items-center pt-1">
              <span className="text-slate-500">% de devolución</span>
              <span className="bg-brand text-white text-xs font-bold px-2.5 py-1 rounded-full">
                {resultado.porcentajeDevolucion}%
              </span>
            </div>
          </div>
        </div>

        {/* Frecuencia de cobro */}
        <div>
          <p className="text-sm font-semibold text-slate-700 mb-2">Frecuencia de cobro</p>
          <div className="grid grid-cols-2 gap-3">
            {['mensual', 'anual'].map((opcion) => (
              <button
                key={opcion}
                type="button"
                onClick={() => setFrecuenciaCobro(opcion)}
                className={`py-2.5 rounded-[12px] text-sm font-semibold border capitalize ${
                  frecuenciaCobro === opcion
                    ? 'bg-brand text-white border-brand'
                    : 'bg-white text-slate-600 border-slate-200'
                }`}
              >
                {opcion}
              </button>
            ))}
          </div>
        </div>

        {/* Formulario de tarjeta (solo visual, sin validación ni pasarela real) */}
        <div>
          <p className="text-sm font-semibold text-slate-700 mb-3">Datos de la tarjeta</p>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-xs text-slate-500">Número de tarjeta</label>
              <input
                type="text"
                inputMode="numeric"
                placeholder="0000 0000 0000 0000"
                value={numeroTarjeta}
                onChange={(e) => setNumeroTarjeta(formatearNumeroTarjeta(e.target.value))}
                className="mt-1 w-full rounded-[12px] border border-slate-200 px-3.5 py-3 text-sm focus:outline-none focus:border-brand"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500">Nombre del titular</label>
              <input
                type="text"
                placeholder="Como figura en la tarjeta"
                value={nombreTitular}
                onChange={(e) => setNombreTitular(e.target.value)}
                className="mt-1 w-full rounded-[12px] border border-slate-200 px-3.5 py-3 text-sm focus:outline-none focus:border-brand"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500">Vencimiento (MM/AA)</label>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="MM/AA"
                  value={expiracion}
                  onChange={(e) => setExpiracion(formatearExpiracion(e.target.value))}
                  className="mt-1 w-full rounded-[12px] border border-slate-200 px-3.5 py-3 text-sm focus:outline-none focus:border-brand"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">CVV</label>
                <input
                  type="password"
                  inputMode="numeric"
                  placeholder="123"
                  maxLength={4}
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  className="mt-1 w-full rounded-[12px] border border-slate-200 px-3.5 py-3 text-sm focus:outline-none focus:border-brand"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Política de privacidad */}
        <label className="flex items-start gap-2.5 text-xs text-slate-500">
          <input
            type="checkbox"
            checked={aceptaPolitica}
            onChange={(e) => setAceptaPolitica(e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-brand shrink-0"
          />
          <span>
            He leído y acepto la{' '}
            <span className="text-brand font-medium">política de privacidad</span> y los
            términos y condiciones del producto.
          </span>
        </label>

        <button
          type="button"
          disabled={!formularioCompleto}
          onClick={() => setCompraConfirmada(true)}
          className="w-full bg-brand text-white font-semibold py-3.5 rounded-[12px] active:opacity-90 disabled:opacity-40"
        >
          Confirmar compra
        </button>

        <p className="text-[11px] text-slate-400 text-center -mt-2">
          Prototipo de UX: no se procesa ningún pago real.
        </p>
      </div>

      {/* Modal de éxito simulado */}
      {compraConfirmada && (
        <div className="fixed inset-0 z-20 flex items-end sm:items-center justify-center bg-slate-900/40 px-4 py-6">
          <div className="w-full max-w-[358px] bg-white rounded-[12px] p-6 text-center">
            <div className="w-14 h-14 mx-auto rounded-full bg-brand-soft flex items-center justify-center text-2xl">
              ✅
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-4">¡Compra confirmada!</h2>
            <p className="text-sm text-slate-500 mt-2">
              Tu plan Ahorro Plus con Sepelio de S/ {formatMonto(aporteMensual)} al mes por{' '}
              {anios} {anios === 1 ? 'año' : 'años'} quedó registrado.
            </p>
            <button
              onClick={onVolverInicio}
              className="mt-6 w-full bg-brand text-white font-semibold py-3 rounded-[12px] active:opacity-90"
            >
              Volver al inicio
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
