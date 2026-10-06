export interface Contact {
  id: number
  name: string
  company?: string
  email?: string
  phone?: string
  title?: string
  notes?: string
  created_at: string
}

interface ContactCardProps {
  contact: Contact
  dealCount: number
  recentActivity?: string
}

export default function ContactCard({ contact, dealCount, recentActivity }: ContactCardProps) {
  const initials = contact.name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <div className="bg-alexa-card rounded-xl p-4 border border-alexa-accent/30 hover:border-alexa-blue/30 transition-all">
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-alexa-blue/20 flex items-center justify-center">
          <span className="text-sm font-bold text-alexa-blue">{initials}</span>
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">{contact.name}</h4>
          {contact.title && (
            <p className="text-xs text-gray-400 truncate">{contact.title}</p>
          )}
          {contact.company && (
            <p className="text-xs text-alexa-blue truncate">{contact.company}</p>
          )}
        </div>
      </div>

      {/* Contact Details */}
      <div className="mt-3 space-y-1.5">
        {contact.email && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="truncate">{contact.email}</span>
          </div>
        )}
        {contact.phone && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span>{contact.phone}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-alexa-accent/20 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {dealCount} deal{dealCount !== 1 ? 's' : ''}
        </span>
        {recentActivity && (
          <span className="text-xs text-gray-500 truncate max-w-[120px]" title={recentActivity}>
            {recentActivity}
          </span>
        )}
      </div>
    </div>
  )
}
