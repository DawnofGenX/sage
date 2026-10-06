import { useState } from 'react'
import type { Deal, Activity } from '../lib/types'

interface DealDetailProps {
  deal: Deal
  activities?: Activity[]
  onUpdateStage?: (dealId: number, stage: string) => void
  onGetInsights?: (dealId: number) => void
  onBack?: () => void
}

const STAGES = [
  { id: 'lead', label: 'Lead', color: 'border-blue-500/30 bg-blue-500/10' },
  { id: 'proposal', label: 'Proposal', color: 'border-purple-500/30 bg-purple-500/10' },
  { id: 'negotiation', label: 'Negotiation', color: 'border-yellow-500/30 bg-yellow-500/10' },
  { id: 'closed_won', label: 'Closed Won', color: 'border-green-500/30 bg-green-500/10' },
  { id: 'closed_lost', label: 'Closed Lost', color: 'border-red-500/30 bg-red-500/10' },
]

const SENTIMENT_CONFIG = {
  positive: { color: 'text-green-400', bg: 'bg-green-500/10', icon: '↑', label: 'Positive' },
  neutral: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: '→', label: 'Neutral' },
  negative: { color: 'text-red-400', bg: 'bg-red-500/10', icon: '↓', label: 'Negative' },
}

export default function DealDetail({ deal, activities = [], onUpdateStage, onGetInsights, onBack }: DealDetailProps) {
  const [isUpdatingStage, setIsUpdatingStage] = useState(false)
  const [isGettingInsights, setIsGettingInsights] = useState(false)
  const [insights, setInsights] = useState<{
    sentiment_trend: string[]
    risks: string[]
    buying_signals: string[]
    recommendation: string
  } | null>(null)
  const [showStageDropdown, setShowStageDropdown] = useState(false)

  const currentStage = STAGES.find(s => s.id === deal.stage) || STAGES[0]
  const sentiment = deal.sentiment ? SENTIMENT_CONFIG[deal.sentiment as keyof typeof SENTIMENT_CONFIG] : null

  const stageHistory = [
    { stage: 'lead', date: '2024-01-15', duration: '5 days' },
    { stage: 'proposal', date: '2024-01-20', duration: '8 days' },
    { stage: 'negotiation', date: '2024-01-28', duration: '12 days' },
  ]

  const handleUpdateStage = async (newStage: string) => {
    setIsUpdatingStage(true)
    setShowStageDropdown(false)
    await new Promise(resolve => setTimeout(resolve, 800))
    onUpdateStage?.(deal.id, newStage)
    setIsUpdatingStage(false)
  }

  const handleGetInsights = async () => {
    setIsGettingInsights(true)
    await new Promise(resolve => setTimeout(resolve, 1500))
    setInsights({
      sentiment_trend: ['positive', 'positive', 'neutral', 'positive'],
      risks: ['Evaluating competitors', 'Timeline pressure'],
      buying_signals: ['Budget approved', 'High interest', 'Ready to proceed'],
      recommendation: 'Strong buying signals detected. Recommend scheduling executive demo to accelerate decision.',
    })
    setIsGettingInsights(false)
    onGetInsights?.(deal.id)
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="p-1.5 rounded-lg bg-alexa-accent/30 text-gray-400 hover:text-white hover:bg-alexa-accent/50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Deal Details
          </h3>
        </div>
      </div>

      {/* Deal Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between mb-3">
          <h4 className="text-xl font-semibold text-white flex-1">{deal.title}</h4>
          {sentiment && (
            <span className={`flex-shrink-0 ml-2 flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${sentiment.bg} ${sentiment.color}`}>
              <span>{sentiment.icon}</span>
              {sentiment.label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 text-xs font-medium rounded-full border ${currentStage.color}`}>
            {currentStage.label}
          </span>
          {deal.value && (
            <span className="text-2xl font-bold text-alexa-blue">${deal.value.toLocaleString()}</span>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative">
          <button
            onClick={() => setShowStageDropdown(!showStageDropdown)}
            disabled={isUpdatingStage}
            className="flex items-center gap-2 px-4 py-2 bg-alexa-blue/20 border border-alexa-blue/30 text-alexa-blue rounded-lg hover:bg-alexa-blue/30 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {isUpdatingStage ? (
              <>
                <div className="w-4 h-4 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
                Updating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Update Stage
              </>
            )}
          </button>
          {showStageDropdown && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-alexa-dark border border-alexa-accent/30 rounded-lg shadow-xl z-10 overflow-hidden">
              {STAGES.map(stage => (
                <button
                  key={stage.id}
                  onClick={() => handleUpdateStage(stage.id)}
                  disabled={stage.id === deal.stage}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors border-b border-alexa-accent/10 last:border-0 ${
                    stage.id === deal.stage
                      ? 'text-gray-500 cursor-default'
                      : 'text-gray-300 hover:bg-alexa-accent/30'
                  }`}
                >
                  {stage.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={handleGetInsights}
          disabled={isGettingInsights}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 border border-purple-500/30 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors text-sm font-medium disabled:opacity-50"
        >
          {isGettingInsights ? (
            <>
              <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
              Analyzing...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Get Insights
            </>
          )}
        </button>
      </div>

      {/* Insights */}
      {insights && (
        <div className="mb-6 p-4 bg-purple-500/5 border border-purple-500/20 rounded-lg">
          <h5 className="text-sm font-medium text-purple-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Deal Insights
          </h5>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-500 mb-1">Sentiment Trend</p>
              <div className="flex gap-1">
                {insights.sentiment_trend.map((s, i) => (
                  <span key={i} className={`px-2 py-0.5 text-xs rounded ${
                    s === 'positive' ? 'bg-green-500/10 text-green-400' :
                    s === 'negative' ? 'bg-red-500/10 text-red-400' : 'bg-gray-500/10 text-gray-400'
                  }`}>
                    {s === 'positive' ? '↑' : s === 'negative' ? '↓' : '→'}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Buying Signals</p>
              <div className="flex flex-wrap gap-1">
                {insights.buying_signals.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded">{s}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Risks</p>
              <div className="flex flex-wrap gap-1">
                {insights.risks.map((r, i) => (
                  <span key={i} className="px-2 py-0.5 text-xs bg-red-500/10 text-red-400 rounded">{r}</span>
                ))}
              </div>
            </div>
            <div className="bg-alexa-dark/30 rounded p-2">
              <p className="text-xs text-gray-500 mb-1">Recommendation</p>
              <p className="text-sm text-gray-300">{insights.recommendation}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stage Progression Timeline */}
      <div className="mb-6">
        <h5 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          Stage Progression
        </h5>
        <div className="relative">
          {stageHistory.map((item, i) => {
            const stage = STAGES.find(s => s.id === item.stage)
            const isCurrent = item.stage === deal.stage
            return (
              <div key={i} className="flex gap-3 mb-3 last:mb-0">
                <div className="flex flex-col items-center">
                  <div className={`w-3 h-3 rounded-full ${isCurrent ? 'bg-alexa-blue' : 'bg-gray-600'}`}></div>
                  {i < stageHistory.length - 1 && <div className="w-0.5 h-6 bg-gray-700"></div>}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm ${isCurrent ? 'text-alexa-blue font-medium' : 'text-gray-400'}`}>
                      {stage?.label}
                    </span>
                    <span className="text-xs text-gray-500">{item.date}</span>
                  </div>
                  <p className="text-xs text-gray-500">Duration: {item.duration}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Associated Activities */}
      <div>
        <h5 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Associated Activities
        </h5>
        {activities.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No activities yet</p>
        ) : (
          <div className="space-y-2">
            {activities.map(activity => (
              <div key={activity.id} className="bg-alexa-dark/30 rounded-lg p-3 border border-alexa-accent/20">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-300">{activity.description}</p>
                  <span className="text-xs text-gray-500">{activity.created_at}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
