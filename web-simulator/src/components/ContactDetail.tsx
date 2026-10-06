import { useState } from 'react'
import type { Contact, Deal, Activity } from '../lib/types'

interface ContactDetailProps {
  contact: Contact
  deals?: Deal[]
  activities?: Activity[]
  onEnrich?: (contactId: number) => void
  onCreateTask?: (contactId: number, task: { title: string; due_date: string }) => void
  onBack?: () => void
}

export default function ContactDetail({ contact, deals = [], activities = [], onEnrich, onCreateTask, onBack }: ContactDetailProps) {
  const [isEnriching, setIsEnriching] = useState(false)
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDueDate, setTaskDueDate] = useState('')
  const [enriched, setEnriched] = useState(false)
  const [enrichmentData, setEnrichmentData] = useState<Record<string, string>>({})

  const initials = contact.name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const handleEnrich = async () => {
    setIsEnriching(true)
    // Simulate enrichment API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    setEnrichmentData({
      linkedin: `linkedin.com/in/${contact.name.toLowerCase().replace(' ', '-')}`,
      twitter: `@${contact.name.toLowerCase().replace(' ', '')}`,
      location: 'San Francisco, CA',
      company_size: '200-500 employees',
      industry: 'Technology',
    })
    setEnriched(true)
    setIsEnriching(false)
    onEnrich?.(contact.id)
  }

  const handleCreateTask = () => {
    if (taskTitle.trim() && taskDueDate) {
      onCreateTask?.(contact.id, { title: taskTitle.trim(), due_date: taskDueDate })
      setTaskTitle('')
      setTaskDueDate('')
      setShowTaskForm(false)
    }
  }

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
      case 'call': return 'text-green-400 bg-green-500/10'
      case 'email': return 'text-blue-400 bg-blue-500/10'
      case 'meeting': return 'text-purple-400 bg-purple-500/10'
      case 'task': return 'text-yellow-400 bg-yellow-500/10'
      default: return 'text-gray-400 bg-gray-500/10'
    }
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      {/* Header with back button */}
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Contact Profile
          </h3>
        </div>
      </div>

      {/* Contact Header */}
      <div className="flex items-start gap-4 mb-6">
        <div className="flex-shrink-0 w-16 h-16 rounded-full bg-alexa-blue/20 flex items-center justify-center">
          <span className="text-xl font-bold text-alexa-blue">{initials}</span>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-xl font-semibold text-white">{contact.name}</h4>
          {contact.title && <p className="text-sm text-gray-400">{contact.title}</p>}
          {contact.company && <p className="text-sm text-alexa-blue">{contact.company}</p>}
          <div className="flex items-center gap-4 mt-2">
            {contact.email && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {contact.email}
              </span>
            )}
            {contact.phone && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                {contact.phone}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={handleEnrich}
          disabled={isEnriching}
          className="flex items-center gap-2 px-4 py-2 bg-alexa-blue/20 border border-alexa-blue/30 text-alexa-blue rounded-lg hover:bg-alexa-blue/30 transition-colors text-sm font-medium disabled:opacity-50"
        >
          {isEnriching ? (
            <>
              <div className="w-4 h-4 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
              Enriching...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Enrich Contact
            </>
          )}
        </button>
        <button
          onClick={() => setShowTaskForm(!showTaskForm)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 border border-purple-500/30 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Task
        </button>
      </div>

      {/* Task Form */}
      {showTaskForm && (
        <div className="mb-6 p-4 bg-alexa-dark/30 rounded-lg border border-alexa-accent/20">
          <h5 className="text-sm font-medium text-white mb-3">New Task</h5>
          <div className="space-y-3">
            <input
              type="text"
              value={taskTitle}
              onChange={e => setTaskTitle(e.target.value)}
              placeholder="Task title..."
              className="w-full bg-alexa-dark/50 border border-alexa-accent/30 rounded-lg px-3 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-alexa-blue"
            />
            <input
              type="date"
              value={taskDueDate}
              onChange={e => setTaskDueDate(e.target.value)}
              className="bg-alexa-dark/50 border border-alexa-accent/30 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-alexa-blue"
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreateTask}
                disabled={!taskTitle.trim() || !taskDueDate}
                className="px-4 py-2 bg-alexa-blue text-alexa-dark font-medium rounded-lg hover:bg-alexa-blue/80 transition-colors text-sm disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Create
              </button>
              <button
                onClick={() => setShowTaskForm(false)}
                className="px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Enrichment Data */}
      {enriched && Object.keys(enrichmentData).length > 0 && (
        <div className="mb-6 p-4 bg-green-500/5 border border-green-500/20 rounded-lg">
          <h5 className="text-sm font-medium text-green-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Enriched Data
          </h5>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(enrichmentData).map(([key, value]) => (
              <div key={key} className="bg-alexa-dark/30 rounded p-2">
                <p className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</p>
                <p className="text-sm text-gray-300">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Associated Deals */}
      {deals.length > 0 && (
        <div className="mb-6">
          <h5 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Associated Deals ({deals.length})
          </h5>
          <div className="space-y-2">
            {deals.map(deal => (
              <div key={deal.id} className="bg-alexa-dark/30 rounded-lg p-3 border border-alexa-accent/20 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{deal.title}</p>
                  <p className="text-xs text-gray-500">Stage: {deal.stage}</p>
                </div>
                {deal.value && (
                  <span className="text-sm font-bold text-alexa-blue">${deal.value.toLocaleString()}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity Timeline */}
      <div>
        <h5 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Activity Timeline
        </h5>
        {activities.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No activities yet</p>
        ) : (
          <div className="space-y-3">
            {activities.map(activity => (
              <div key={activity.id} className="flex gap-3">
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${activityColor(activity.type)}`}>
                  {activityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-300">{activity.description}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{activity.created_at}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
