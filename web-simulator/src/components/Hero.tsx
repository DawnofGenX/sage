interface HeroProps {
  hoursSaved: number
  manualEntries: number
}

const STEPS = [
  {
    id: 1,
    label: 'Call',
    icon: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
  },
  {
    id: 2,
    label: 'Extract',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
  },
  {
    id: 3,
    label: 'Insight',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  },
]

export default function Hero({ hoursSaved, manualEntries }: HeroProps) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-alexa-accent/30 bg-gradient-to-br from-alexa-dark via-alexa-accent/40 to-alexa-blue/20 p-8 mb-6">
      {/* Decorative glow */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-alexa-blue/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-16 -left-16 w-48 h-48 bg-alexa-accent/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10">
        {/* Title */}
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-white mb-1 animate-slide-in">Sage</h2>
          <p className="text-lg text-gray-300 animate-slide-in" style={{ animationDelay: '0.1s' }}>
            Your CRM that listens
          </p>
        </div>

        {/* Stats Row */}
        <div className="flex flex-wrap gap-6 mb-8">
          <div className="animate-slide-in" style={{ animationDelay: '0.2s' }}>
            <p className="text-2xl font-bold text-alexa-blue">{hoursSaved}h</p>
            <p className="text-sm text-gray-400">saved today</p>
          </div>
          <div className="animate-slide-in" style={{ animationDelay: '0.3s' }}>
            <p className="text-2xl font-bold text-green-400">{manualEntries}</p>
            <p className="text-sm text-gray-400">manual entries</p>
          </div>
        </div>

        {/* 3-Step Visual */}
        <div className="flex items-center gap-0">
          {STEPS.map((step, i) => (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              {/* Step Circle */}
              <div className="flex flex-col items-center animate-slide-in" style={{ animationDelay: `${0.4 + i * 0.15}s` }}>
                <div className="w-12 h-12 rounded-full bg-alexa-blue/20 border-2 border-alexa-blue/40 flex items-center justify-center mb-2">
                  <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={step.icon} />
                  </svg>
                </div>
                <span className="text-xs font-medium text-gray-300">{step.label}</span>
              </div>

              {/* Connector Bar */}
              {i < STEPS.length - 1 && (
                <div className="flex-1 mx-3 mb-6">
                  <div className="h-0.5 bg-alexa-accent/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-alexa-blue to-alexa-blue/60 rounded-full animate-progress-fill"
                      style={{ animationDelay: `${0.5 + i * 0.15}s` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
