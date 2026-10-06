import { useState, useEffect, useRef } from 'react'
import type { Activity, Contact } from '../lib/types'

interface ActivityFeedProps {
  activities: Activity[]
  contacts?: Contact[]
  onFilterChange?: (filters: { type: string; contactId: number | null }) => void
}

const ACTIVITY_TYPES = [
  { id: 'all', label: 'All', color: 'bg-gray-500/20 text-gray-400' },
  { id: 'call', label: 'Calls', color: 'bg-green-500/20 text-green-400' },
  { id: 'email', label: 'Emails', color: 'bg-blue-500/20 text-blue-400' },
  { id: 'meeting', label: 'Meetings', color: 'bg-purple-500/20 text-purple-400' },
  { id: 'task', label: 'Tasks', color: 'bg-yellow-500/20 text-yellow-400' },
]

export default function ActivityFeed({ activities, contacts = [], onFilterChange }: ActivityFeedProps) {
  const [typeFilter, setTypeFilter] = useState('all')
  const [contactFilter, setContactFilter] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isLive, setIsLive] = useState(true)
  const [newActivityCount, setNewActivityCount] = useState(0)
  const feedRef = useRef<HTMLDivElement>(null)
  const prevActivityCountRef = useRef(activities.length)

  // Simulate real-time updates
  useEffect(() => {
    if (!isLive) return

    const interval = setInterval(() => {
      // Simulate a new activity arriving
      if (Math.random() > 0.7) {
        setNewActivityCount(prev => prev + 1)
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [isLive])

  // Track new activities
  useEffect(() => {
    if (activities.length > prevActivityCountRef.current) {
      const newCount = activities.length - prevActivityCountRef.current
      setNewActivityCount(prev => prev + newCount)
    }
    prevActivityCountRef.current = activities.length
  }, [activities.length])

  const handleTypeFilter = (type: string) => {
    setTypeFilter(type)
    onFilterChange?.({ type, contactId: contactFilter })
  }

  const handleContactFilter = (contactId: number | null) => {
    setContactFilter(contactId)
    onFilterChange?.({ type: typeFilter, contactId })
  }

  const clearNewCount = () => {
    setNewActivityCount(0)
  }

  const filteredActivities = activities.filter(activity => {
    if (typeFilter !== 'all' && activity.type !== typeFilter) return false
    if (contactFilter !== null && activity.contact_id !== contactFilter) return false
    if (searchQuery && !activity.description.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  const activityIcon = (type: string) => {
    switch (type) {
      case 'call':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
        )
      case 'email':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        )
      case 'meeting':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )
      case 'task':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        )
      default:
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  const activityColor = (type: string) => {
    switch (type) {
      case 'call': return 'text-green-400 bg-green-500/10 border-green-500/20'
      case 'email': return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      case 'meeting': return 'text-purple-400 bg-purple-500/10 border-purple-500/20'
      case 'task': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20'
    }
  }

  const getContactName = (contactId: number) => {
    const contact = contacts.find(c => c.id === contactId)
    return contact?.name || `Contact #${contactId}`
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Activity Feed
          {newActivityCount > 0 && (
            <span className="px-2 py-0.5 text-xs bg-alexa-blue/20 text-alexa-blue rounded-full animate-pulse">
              {newActivityCount} new
            </span>
          )}
        </h3>
        <div className="flex items-center gap-2">
          {newActivityCount > 0 && (
            <button
              onClick={clearNewCount}
              className="px-2 py-1 text-xs bg-alexa-accent/30 text-gray-400 rounded hover:text-white transition-colors"
            >
              Mark read
            </button>
          )}
          <button
            onClick={() => setIsLive(!isLive)}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs rounded-full transition-colors ${
              isLive
                ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                : 'bg-gray-500/10 border border-gray-500/30 text-gray-400'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></span>
            {isLive ? 'Live' : 'Paused'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {/* Type filters */}
        <div className="flex items-center gap-1">
          {ACTIVITY_TYPES.map(type => (
            <button
              key={type.id}
              onClick={() => handleTypeFilter(type.id)}
              className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                typeFilter === type.id
                  ? 'bg-alexa-blue/20 text-alexa-blue border border-alexa-blue/30'
                  : 'bg-alexa-accent/20 text-gray-400 hover:text-gray-300 border border-transparent'
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>

        {/* Contact filter */}
        {contacts.length > 0 && (
          <select
            value={contactFilter ?? ''}
            onChange={e => handleContactFilter(e.target.value ? Number(e.target.value) : null)}
            className="bg-alexa-dark/50 border border-alexa-accent/30 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-alexa-blue"
          >
            <option value="">All Contacts</option>
            {contacts.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}

        {/* Search */}
        <div className="relative ml-auto">
          <svg className="w-3.5 h-3.5 text-gray-500 absolute left-2.5 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search activities..."
            className="bg-alexa-dark/50 border border-alexa-accent/30 rounded-lg pl-8 pr-3 py-1 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-alexa-blue w-40"
          />
        </div>
      </div>

      {/* Activity List */}
      <div ref={feedRef} className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {filteredActivities.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <svg className="w-10 h-10 text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-sm text-gray-500">No activities found</p>
            <p className="text-xs text-gray-600 mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          filteredActivities.map(activity => (
            <div
              key={activity.id}
              className="flex gap-3 p-3 bg-alexa-dark/30 rounded-lg border border-alexa-accent/20 hover:border-alexa-accent/40 transition-colors"
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border ${activityColor(activity.type)}`}>
                {activityIcon(activity.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-300 leading-relaxed">{activity.description}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-500">{getContactName(activity.contact_id)}</span>
                  <span className="text-xs text-gray-600">·</span>
                  <span className="text-xs text-gray-500">{formatTime(activity.created_at)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer Stats */}
      <div className="mt-4 pt-3 border-t border-alexa-accent/20 flex items-center justify-between text-xs text-gray-500">
        <span>{filteredActivities.length} activities</span>
        <span>{activities.length} total</span>
      </div>
    </div>
  )
}
