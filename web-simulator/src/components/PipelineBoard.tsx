import { useState } from 'react'

export interface BoardDeal {
  id: number
  title: string
  value: number
  stage: string
  contactName: string
  sentiment?: string
  isStuck?: boolean
}

interface PipelineBoardProps {
  deals: BoardDeal[]
  isSyncing: boolean
  onSync: () => void
}

const STAGES = [
  { id: 'lead', label: 'Lead', color: 'border-blue-500/30' },
  { id: 'proposal', label: 'Proposal', color: 'border-purple-500/30' },
  { id: 'negotiation', label: 'Negotiation', color: 'border-yellow-500/30' },
  { id: 'closed_won', label: 'Closed Won', color: 'border-green-500/30' },
  { id: 'closed_lost', label: 'Closed Lost', color: 'border-red-500/30' },
]

function DealCard({ deal }: { deal: BoardDeal }) {
  const sentimentColor = deal.sentiment === 'positive' ? 'text-green-400' :
    deal.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'

  return (
    <div className={`bg-alexa-dark/50 rounded-lg p-3 border transition-all hover:bg-alexa-dark/70 ${
      deal.isStuck ? 'border-red-500/50 shadow-red-500/10 shadow-md' : 'border-alexa-accent/20'
    }`}>
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-white leading-tight">{deal.title}</h4>
        {deal.isStuck && (
          <span className="flex-shrink-0 ml-2 px-1.5 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">
            Stuck
          </span>
        )}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{deal.contactName}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-alexa-blue">${deal.value.toLocaleString()}</span>
          {deal.sentiment && (
            <span className={`text-xs ${sentimentColor}`}>
              {deal.sentiment === 'positive' ? '↑' : deal.sentiment === 'negative' ? '↓' : '→'}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PipelineBoard({ deals, isSyncing, onSync }: PipelineBoardProps) {
  const [hoveredStage, setHoveredStage] = useState<string | null>(null)

  const totalValue = deals.reduce((sum, d) => sum + d.value, 0)
  const stuckCount = deals.filter(d => d.isStuck).length

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
          Pipeline Board
        </h3>
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="flex items-center gap-2 px-3 py-1.5 bg-alexa-blue/10 border border-alexa-blue/30 text-alexa-blue text-xs font-medium rounded-lg hover:bg-alexa-blue/20 transition-colors disabled:opacity-50"
        >
          {isSyncing ? (
            <>
              <div className="w-3 h-3 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
              Syncing...
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Sync to CRM
            </>
          )}
        </button>
      </div>

      {/* Kanban Columns */}
      <div className="grid grid-cols-5 gap-3 min-h-[200px]">
        {STAGES.map((stage) => {
          const stageDeals = deals.filter(d => d.stage === stage.id)
          return (
            <div
              key={stage.id}
              className={`flex flex-col rounded-lg border ${stage.color} bg-alexa-dark/20 transition-all ${
                hoveredStage === stage.id ? 'bg-alexa-dark/40' : ''
              }`}
              onMouseEnter={() => setHoveredStage(stage.id)}
              onMouseLeave={() => setHoveredStage(null)}
            >
              {/* Column Header */}
              <div className="px-3 py-2 border-b border-alexa-accent/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-400">{stage.label}</span>
                  <span className="text-xs text-gray-600 bg-alexa-dark/50 px-1.5 py-0.5 rounded">
                    {stageDeals.length}
                  </span>
                </div>
              </div>

              {/* Cards */}
              <div className="flex-1 p-2 space-y-2">
                {stageDeals.map((deal) => (
                  <DealCard key={deal.id} deal={deal} />
                ))}
                {stageDeals.length === 0 && (
                  <div className="flex items-center justify-center h-20 text-gray-600 text-xs">
                    No deals
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary Footer */}
      <div className="mt-4 pt-4 border-t border-alexa-accent/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-gray-500">Total Deals</p>
              <p className="text-lg font-bold text-white">{deals.length}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Pipeline Value</p>
              <p className="text-lg font-bold text-alexa-blue">${totalValue.toLocaleString()}</p>
            </div>
            {stuckCount > 0 && (
              <div>
                <p className="text-xs text-gray-500">Stuck Deals</p>
                <p className="text-lg font-bold text-red-400">{stuckCount}</p>
              </div>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Avg Deal Size</p>
            <p className="text-sm font-medium text-gray-300">
              ${deals.length > 0 ? Math.round(totalValue / deals.length).toLocaleString() : 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
