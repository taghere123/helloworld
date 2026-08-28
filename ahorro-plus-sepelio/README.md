# Ahorro Plus con Sepelio — Prototipo interactivo

Prototipo de UX (React + Tailwind CSS v4 + Vite) del flujo de 3 pantallas de
"Ahorro Plus con Sepelio", un producto de ahorro con devolución de
Interseguro que incluye un seguro de sepelio de monto fijo (S/10,000).

Es un prototipo de solo interfaz: no hay backend, no se procesa ningún pago
real y todos los datos (cálculos, testimonios) son simulados.

## Cómo correrlo

```bash
npm install
npm run dev
```

Diseñado mobile-first para un viewport de ~390px (el marco se ve centrado en
pantallas más anchas).

## Estructura

- `src/lib/calculadora.js` — función pura `calcularPlan(aporteMensual, anios)`
  que devuelve aporte total, ganancia, devolución total y % de devolución.
  Aislada a propósito para poder reemplazarla luego por la lógica actuarial
  real sin tocar la UI.
- `src/context/PlanContext.jsx` — estado compartido del plan elegido
  (aporte mensual, años, frecuencia de cobro y resultado) entre las 3
  pantallas.
- `src/components/Landing.jsx` — Pantalla 1: landing con hero, beneficios y
  testimonios.
- `src/components/Cotizador.jsx` — Pantalla 2: sliders de aporte/años y
  tarjeta de resultado en vivo.
- `src/components/Pago.jsx` — Pantalla 3: resumen del plan, formulario de
  tarjeta (solo visual), frecuencia de cobro y modal de compra confirmada.
- `src/App.jsx` — navegación entre pantallas con estado de React (sin
  router).

## Notas de marca

El azul principal (`--color-brand` en `src/index.css`) usa el placeholder
`#3537a4`; está marcado con un comentario `TODO` para reemplazarlo por el
hex oficial de marca de Interseguro cuando se defina.
