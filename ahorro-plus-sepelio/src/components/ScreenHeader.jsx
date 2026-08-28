export default function ScreenHeader({ title, onBack }) {
  return (
    <header className="flex items-center gap-3 px-4 py-4 border-b border-slate-100 bg-white sticky top-0 z-10">
      {onBack && (
        <button
          onClick={onBack}
          aria-label="Volver"
          className="w-8 h-8 flex items-center justify-center rounded-full text-brand hover:bg-brand-soft shrink-0"
        >
          ←
        </button>
      )}
      <div className="flex items-center gap-2 min-w-0">
        <div className="w-7 h-7 rounded-md bg-brand text-white text-[11px] font-bold flex items-center justify-center shrink-0">
          IS
        </div>
        <p className="text-sm font-semibold text-slate-800 truncate">
          {title ?? 'Interseguro | Ahorro Plus'}
        </p>
      </div>
    </header>
  )
}
