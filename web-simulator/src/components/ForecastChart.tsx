import { useState } from 'react'

interface ForecastChartProps {
  deals?: Array<{ stage: string; value: number }>
}

interface ForecastData {
  month: string
  best: number
  worst: number
  weighted: number
}

const MONTHLY_FORECAST: ForecastData[] = [
  { month: 'Oct', best: 450000, worst: 280000, weighted: 365000 },
  { month: 'Nov', best: 520000, worst: 310000, weighted: 415000 },
  { month: 'Dec', best: 680000, worst: 380000, weighted: 530000 },
  { month: 'Jan', best: 590000, worst: 340000, weighted: 465000 },
  { month: 'Feb', best: 620000, worst: 360000, weighted: 490000 },
  { month: 'Mar', best: 750000, worst: 420000, weighted: 585000 },
]

const STAGE_WEIGHTS: Record<string, number> = {
  lead: 0.1,
  proposal: 0.3,
  negotiation: 0.6,
  closed_won: 1.0,
  closed_lost: 0.0,
}

export default function ForecastChart({ deals = [] }: ForecastChartProps) {
  const [hoveredMonth, setHoveredMonth] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<'chart' | 'bars'>('chart')

  const maxValue = Math.max(...MONTHLY_FORECAST.map(d => d.best))
  const totalWeighted = MONTHLY_FORECAST.reduce((sum, d) => sum + d.weighted, 0)
  const totalBest = MONTHLY_FORECAST.reduce((sum, d) => sum + d.best, 0)
  const totalWorst = MONTHLY_FORECAST.reduce((sum, d) => sum + d.worst, 0)

  // Pipeline value by stage
  const pipelineByStage = Object.entries(
    deals.reduce((acc, deal) => {
      acc[deal.stage] = (acc[deal.stage] || 0) + deal.value
      return acc
    }, {} as Record<string, number>)
  ).map(([stage, value]) => ({ stage, value }))

  const totalPipeline = pipelineByStage.reduce((sum, s) => sum + s.value, 0)

  // Confidence calculation
  const confidence = Math.round(
    (totalWeighted / totalBest) * 100
  )

  const getConfidenceColor = (conf: number) => {
    if (conf >= 70) return 'text-green-400'
    if (conf >= 50) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getConfidenceLabel = (conf: number) => {
    if (conf >= 70) return 'High'
    if (conf >= 50) return 'Medium'
    return 'Low'
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Revenue Forecast
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('chart')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              viewMode === 'chart' ? 'bg-alexa-blue/20 text-alexa-blue' : 'bg-alexa-accent/20 text-gray-400 hover:text-gray-300'
            }`}
          >
            Chart
          </button>
          <button
            onClick={() => setViewMode('bars')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              viewMode === 'bars' ? 'bg-alexa-blue/20 text-alexa-blue' : 'bg-alexa-accent/20 text-gray-400 hover:text-gray-300'
            }`}
          >
            Bars
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-alexa-dark/30 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Weighted Forecast</p>
          <p className="text-lg font-bold text-alexa-blue">${(totalWeighted / 1000).toFixed(0)}K</p>
        </div>
        <div className="bg-alexa-dark/30 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Best Case</p>
          <p className="text-lg font-bold text-green-400">${(totalBest / 1000).toFixed(0)}K</p>
        </div>
        <div className="bg-alexa-dark/30 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Worst Case</p>
          <p className="text-lg font-bold text-red-400">${(totalWorst / 1000).toFixed(0)}K</p>
        </div>
      </div>

      {/* Confidence Indicator */}
      <div className="mb-6 p-3 bg-alexa-dark/30 rounded-lg border border-alexa-accent/20">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Forecast Confidence</span>
          <span className={`text-sm font-bold ${getConfidenceColor(confidence)}`}>
            {confidence}% — {getConfidenceLabel(confidence)}
          </span>
        </div>
        <div className="w-full h-2 bg-alexa-dark rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              confidence >= 70 ? 'bg-green-500' : confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${confidence}%` }}
          ></div>
        </div>
      </div>

      {/* Chart View */}
      {viewMode === 'chart' && (
        <div className="mb-6">
          <div className="flex items-end gap-2 h-48">
            {MONTHLY_FORECAST.map((data, i) => (
              <div
                key={data.month}
                className="flex-1 flex flex-col items-center gap-1"
                onMouseEnter={() => setHoveredMonth(i)}
                onMouseLeave={() => setHoveredMonth(null)}
              >
                <div className="w-full flex flex-col items-center justify-end h-40 relative">
                  {/* Best case bar */}
                  <div
                    className="w-full bg-green-500/30 rounded-t-sm transition-all duration-300"
                    style={{ height: `${(data.best / maxValue) * 100}%` }}
                  ></div>
                  {/* Weighted bar */}
                  <div
                    className="w-full bg-alexa-blue/50 rounded-t-sm transition-all duration-300"
                    style={{ height: `${(data.weighted / maxValue) * 100}%` }}
                  ></div>
                  {/* Worst case bar */}
                  <div
                    className="w-full bg-red-500/30 rounded-t-sm transition-all duration-300"
                    style={{ height: `${(data.worst / maxValue) * 100}%` }}
                  ></div>

                  {/* Tooltip */}
                  {hoveredMonth === i && (
                    <div className="absolute -top-20 left-1/2 -translate-x-1/2 bg-alexa-dark border border-alexa-accent/30 rounded-lg p-2 shadow-xl z-10 whitespace-nowrap">
                      <p className="text-xs font-medium text-white mb-1">{data.month}</p>
                      <p className="text-xs text-green-400">Best: ${(data.best / 1000).toFixed(0)}K</p>
                      <p className="text-xs text-alexa-blue">Weighted: ${(data.weighted / 1000).toFixed(0)}K</p>
                      <p className="text-xs text-red-400">Worst: ${(data.worst / 1000).toFixed(0)}K</p>
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-500">{data.month}</span>
              </div>
            ))}
          </div>
          {/* Legend */}
          <div className="flex items-center justify-center gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-green-500/30 rounded-sm"></div>
              <span className="text-xs text-gray-400">Best</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-alexa-blue/50 rounded-sm"></div>
              <span className="text-xs text-gray-400">Weighted</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-red-500/30 rounded-sm"></div>
              <span className="text-xs text-gray-400">Worst</span>
            </div>
          </div>
        </div>
      )}

      {/* Bars View */}
      {viewMode === 'bars' && (
        <div className="mb-6 space-y-3">
          {MONTHLY_FORECAST.map((data, i) => (
            <div
              key={data.month}
              className="flex items-center gap-3"
              onMouseEnter={() => setHoveredMonth(i)}
              onMouseLeave={() => setHoveredMonth(null)}
            >
              <span className="text-xs text-gray-500 w-8">{data.month}</span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-3 bg-alexa-dark rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500/40 rounded-full"
                      style={{ width: `${(data.best / maxValue) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-green-400 w-12 text-right">${(data.best / 1000).toFixed(0)}K</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-3 bg-alexa-dark rounded-full overflow-hidden">
                    <div
                      className="h-full bg-alexa-blue/50 rounded-full"
                      style={{ width: `${(data.weighted / maxValue) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-alexa-blue w-12 text-right">${(data.weighted / 1000).toFixed(0)}K</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-3 bg-alexa-dark rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-500/40 rounded-full"
                      style={{ width: `${(data.worst / maxValue) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-red-400 w-12 text-right">${(data.worst / 1000).toFixed(0)}K</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pipeline Value by Stage */}
      <div>
        <h5 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
          Pipeline Value by Stage
        </h5>
        {pipelineByStage.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No pipeline data</p>
        ) : (
          <div className="space-y-2">
            {pipelineByStage.map(({ stage, value }) => {
              const weight = STAGE_WEIGHTS[stage] || 0
              const weightedValue = value * weight
              return (
                <div key={stage} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-24 capitalize">{stage.replace('_', ' ')}</span>
                  <div className="flex-1 h-4 bg-alexa-dark rounded-full overflow-hidden">
                    <div
                      className="h-full bg-alexa-blue/40 rounded-full"
                      style={{ width: `${totalPipeline > 0 ? (value / totalPipeline) * 100 : 0}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-400 w-16 text-right">${(value / 1000).toFixed(0)}K</span>
                  <span className="text-xs text-alexa-blue w-16 text-right">${(weightedValue / 1000).toFixed(0)}K</span>
                </div>
              )
            })}
            <div className="flex items-center gap-3 pt-2 border-t border-alexa-accent/20">
              <span className="text-xs font-medium text-white w-24">Total</span>
              <div className="flex-1"></div>
              <span className="text-xs font-bold text-white w-16 text-right">${(totalPipeline / 1000).toFixed(0)}K</span>
              <span className="text-xs font-bold text-alexa-blue w-16 text-right">
                ${(pipelineByStage.reduce((sum, s) => sum + s.value * (STAGE_WEIGHTS[s.stage] || 0), 0) / 1000).toFixed(0)}K
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
