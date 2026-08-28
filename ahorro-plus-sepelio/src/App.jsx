import { useState } from 'react'
import { PlanProvider } from './context/PlanContext'
import Landing from './components/Landing'
import Cotizador from './components/Cotizador'
import Pago from './components/Pago'

const PANTALLAS = {
  LANDING: 'landing',
  COTIZADOR: 'cotizador',
  PAGO: 'pago',
}

function App() {
  const [pantalla, setPantalla] = useState(PANTALLAS.LANDING)

  return (
    <PlanProvider>
      <div className="min-h-screen bg-slate-200 flex justify-center">
        {/* Marco mobile-first (~390px) para revisión del prototipo */}
        <div className="w-full max-w-[390px] min-h-screen bg-white shadow-sm">
          {pantalla === PANTALLAS.LANDING && (
            <Landing onCotizar={() => setPantalla(PANTALLAS.COTIZADOR)} />
          )}
          {pantalla === PANTALLAS.COTIZADOR && (
            <Cotizador
              onBack={() => setPantalla(PANTALLAS.LANDING)}
              onConfirmar={() => setPantalla(PANTALLAS.PAGO)}
            />
          )}
          {pantalla === PANTALLAS.PAGO && (
            <Pago onVolverInicio={() => setPantalla(PANTALLAS.LANDING)} />
          )}
        </div>
      </div>
    </PlanProvider>
  )
}

export default App
