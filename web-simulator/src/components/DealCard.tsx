export interface Deal {
  id: number
  contact_id: number
  title: string
  value?: number
  stage: string
  notes?: string
  sentiment?: string
  created_at: string
}

interface DealCardProps {
  deal: Deal
  contactName?: string
}

const STAGE_COLORS: Record<string, string> = {
  lead: 'bg-blue-500/20 text-blue-400',
  proposal: 'bg-purple-500/20 text-purple-400',
  negotiation: 'bg-yellow-500/20 text-yellow-400',
  closed_won: 'bg-green-500/20 text-green-400',
  closed_lost: 'bg-red-500/20 text-red-400',
}

const SENTIMENT_CONFIG = {
  positive: { color: 'text-green-400', bg: 'bg-green-500/10', icon: '↑', label: 'Positive' },
  neutral: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: '→', label: 'Neutral' },
  negative: { color: 'text-red-400', bg: 'bg-red-500/10', icon: '↓', label: 'Negative' },
}

export default function DealCard({ deal, contactName }: DealCardProps) {
  const stageColor = STAGE_COLORS[deal.stage] || 'bg-gray-500/20 text-gray-400'
  const sentiment = deal.sentiment ? SENTIMENT_CONFIG[deal.sentiment as keyof typeof SENTIMENT_CONFIG] : null

  return (
    <div className="bg-alexa-card rounded-xl p-4 border border-alexa-accent/30 hover:border-alexa-blue/30 transition-all">
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-semibold text-white leading-tight flex-1">{deal.title}</h4>
        {sentiment && (
          <span className={`flex-shrink-0 ml-2 flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${sentiment.bg} ${sentiment.color}`}>
            <span>{sentiment.icon}</span>
            {sentiment.label}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${stageColor}`}>
          {deal.stage.replace('_', ' ')}
        </span>
        {deal.value && (
          <span className="text-sm font-bold text-alexa-blue">${deal.value.toLocaleString()}</span>
        )}
      </div>

      {contactName && (
        <div className="flex items-center gap-2 mb-2">
          <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <span className="text-xs text-gray-400">{contactName}</span>
        </div>
      )}

      {deal.notes && (
        <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{deal.notes}</p>
      )}
    </div>
  )
}
