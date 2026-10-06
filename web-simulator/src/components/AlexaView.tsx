import { useState, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface PipelineStats {
  total_deals: number;
  total_value: number;
  deals_by_stage: Record<string, number>;
  stuck_deals: Array<{ id: number; title: string }>;
}

interface ContactInfo {
  name: string;
  company: string;
  title: string;
  deals: Array<{ title: string; value: number; stage: string }>;
  activities: Array<{ type: string; description: string }>;
}

interface FollowUp {
  title: string;
  due_date: string;
  priority: string;
}

interface AlexaResponse {
  text: string;
  type: 'success' | 'error' | 'info';
  timestamp: Date;
}

// ─── Mock Data ───────────────────────────────────────────────────────────────

const MOCK_PIPELINE: PipelineStats = {
  total_deals: 5,
  total_value: 470000,
  deals_by_stage: { lead: 2, proposal: 1, negotiation: 1, closed_won: 1 },
  stuck_deals: [{ id: 2, title: 'Globex Platform Deal' }],
};

const MOCK_CONTACTS: Record<string, ContactInfo> = {
  'sarah chen': {
    name: 'Sarah Chen',
    company: 'Acme Corp',
    title: 'VP of Engineering',
    deals: [{ title: 'Acme Enterprise License', value: 50000, stage: 'proposal' }],
    activities: [{ type: 'call', description: 'Follow-up call about enterprise license' }],
  },
  'mike johnson': {
    name: 'Mike Johnson',
    company: 'Globex',
    title: 'CTO',
    deals: [{ title: 'Globex Platform Deal', value: 120000, stage: 'negotiation' }],
    activities: [{ type: 'meeting', description: 'Product demo with Globex team' }],
  },
};

const MOCK_FOLLOWUPS: FollowUp[] = [
  { title: 'Schedule demo with Sarah Chen', due_date: 'Next Tuesday', priority: 'high' },
  { title: 'Follow up on conversation with Mike Johnson', due_date: 'Friday', priority: 'medium' },
];

const VOICE_SUGGESTIONS = [
  "What's my pipeline?",
  'Tell me about Sarah Chen',
  'Any follow-ups due?',
];

// ─── Component ───────────────────────────────────────────────────────────────

export default function AlexaView() {
  const [isListening, setIsListening] = useState(false);
  const [inputText, setInputText] = useState('');
  const [responses, setResponses] = useState<AlexaResponse[]>([]);
  const [pipelineStats, setPipelineStats] = useState<PipelineStats | null>(null);
  const [selectedContact, setSelectedContact] = useState<ContactInfo | null>(null);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value}`;
  };

  const processCommand = useCallback(async (command: string) => {
    if (!command.trim()) return;

    setIsProcessing(true);
    setIsListening(false);

    const lower = command.toLowerCase();
    let response: AlexaResponse;

    try {
      if (lower.includes('pipeline') || lower.includes('deals')) {
        // Simulate API call
        await new Promise((r) => setTimeout(r, 800));
        setPipelineStats(MOCK_PIPELINE);
        const stages = Object.entries(MOCK_PIPELINE.deals_by_stage)
          .map(([stage, count]) => `${count} in ${stage}`)
          .join(', ');
        response = {
          text: `You have ${MOCK_PIPELINE.total_deals} deals worth ${formatCurrency(MOCK_PIPELINE.total_value)}. ${stages}. ${MOCK_PIPELINE.stuck_deals.length} deal may need attention.`,
          type: 'success',
          timestamp: new Date(),
        };
      } else if (lower.includes('tell me about') || lower.includes('contact')) {
        await new Promise((r) => setTimeout(r, 600));
        const nameMatch = lower.match(/tell me about (.+)/);
        const name = nameMatch ? nameMatch[1].trim() : '';
        const contact = MOCK_CONTACTS[name];

        if (contact) {
          setSelectedContact(contact);
          const dealValue = contact.deals.reduce((sum, d) => sum + d.value, 0);
          response = {
            text: `${contact.name}, ${contact.title} at ${contact.company}. They have ${contact.deals.length} deal worth ${formatCurrency(dealValue)}. ${contact.activities.length} recent activities on record.`,
            type: 'success',
            timestamp: new Date(),
          };
        } else {
          response = {
            text: `I could not find a contact matching "${name}". Try "Sarah Chen" or "Mike Johnson".`,
            type: 'error',
            timestamp: new Date(),
          };
        }
      } else if (lower.includes('follow') || lower.includes('due') || lower.includes('today')) {
        await new Promise((r) => setTimeout(r, 500));
        setFollowUps(MOCK_FOLLOWUPS);
        const highPriority = MOCK_FOLLOWUPS.filter((f) => f.priority === 'high');
        response = {
          text: `You have ${MOCK_FOLLOWUPS.length} follow-ups due today. ${highPriority.length} high priority. First up: ${MOCK_FOLLOWUPS[0].title}, due ${MOCK_FOLLOWUPS[0].due_date}.`,
          type: 'success',
          timestamp: new Date(),
        };
      } else if (lower.includes('help') || lower.includes('what can')) {
        response = {
          text: 'I can help you check your pipeline, get contact context, and review follow-ups. Try saying "What\'s my pipeline?", "Tell me about Sarah Chen", or "Any follow-ups due?"',
          type: 'info',
          timestamp: new Date(),
        };
      } else if (lower.includes('stop') || lower.includes('cancel') || lower.includes('goodbye')) {
        response = {
          text: 'Goodbye! Sage will keep listening for updates.',
          type: 'info',
          timestamp: new Date(),
        };
      } else {
        response = {
          text: `I heard "${command}". Try asking about your pipeline, a contact, or follow-ups.`,
          type: 'info',
          timestamp: new Date(),
        };
      }
    } catch {
      response = {
        text: 'Sorry, I had trouble processing that request. Please try again.',
        type: 'error',
        timestamp: new Date(),
      };
    }

    setResponses((prev) => [response, ...prev].slice(0, 10));
    setIsProcessing(false);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim()) {
      processCommand(inputText);
      setInputText('');
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputText(suggestion);
    processCommand(suggestion);
  };

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
    } else {
      setIsListening(true);
      // Simulate voice input after a delay
      setTimeout(() => {
        setIsListening(false);
        const randomSuggestion = VOICE_SUGGESTIONS[Math.floor(Math.random() * VOICE_SUGGESTIONS.length)];
        setInputText(randomSuggestion);
        processCommand(randomSuggestion);
      }, 2000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Echo Show Header */}
      <div className="bg-alexa-card rounded-2xl border border-alexa-accent/30 overflow-hidden">
        <div className="bg-gradient-to-r from-alexa-blue/10 to-alexa-accent/10 px-6 py-4 border-b border-alexa-accent/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-alexa-blue/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Sage on Alexa+</h2>
                <p className="text-xs text-gray-400">Passive Sales Intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isListening ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-xs text-gray-400">{isListening ? 'Listening...' : 'Ready'}</span>
            </div>
          </div>
        </div>

        {/* Pipeline Stats Display */}
        {pipelineStats && (
          <div className="px-6 py-4 border-b border-alexa-accent/20">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-alexa-blue">{pipelineStats.total_deals}</p>
                <p className="text-xs text-gray-400">Active Deals</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-alexa-blue">{formatCurrency(pipelineStats.total_value)}</p>
                <p className="text-xs text-gray-400">Pipeline Value</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-alexa-blue">{pipelineStats.stuck_deals.length}</p>
                <p className="text-xs text-gray-400">Need Attention</p>
              </div>
            </div>
          </div>
        )}

        {/* Contact Display */}
        {selectedContact && (
          <div className="px-6 py-4 border-b border-alexa-accent/20">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-alexa-blue/20 flex items-center justify-center">
                <span className="text-lg font-bold text-alexa-blue">
                  {selectedContact.name.split(' ').map((n) => n[0]).join('')}
                </span>
              </div>
              <div>
                <p className="font-semibold text-white">{selectedContact.name}</p>
                <p className="text-sm text-gray-400">{selectedContact.title} at {selectedContact.company}</p>
              </div>
            </div>
          </div>
        )}

        {/* Follow-ups Display */}
        {followUps.length > 0 && (
          <div className="px-6 py-4 border-b border-alexa-accent/20">
            <p className="text-sm font-medium text-gray-300 mb-2">Today's Follow-ups</p>
            <div className="space-y-2">
              {followUps.map((fu, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${fu.priority === 'high' ? 'bg-red-400' : 'bg-yellow-400'}`} />
                  <span className="text-sm text-gray-300 flex-1">{fu.title}</span>
                  <span className="text-xs text-gray-500">{fu.due_date}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Response Area */}
        <div className="px-6 py-4 min-h-[120px]">
          {isProcessing ? (
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-400">Sage is thinking...</span>
            </div>
          ) : responses.length > 0 ? (
            <div className="space-y-3">
              {responses.slice(0, 3).map((resp, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg ${
                    resp.type === 'success'
                      ? 'bg-green-500/10 border border-green-500/20'
                      : resp.type === 'error'
                      ? 'bg-red-500/10 border border-red-500/20'
                      : 'bg-alexa-accent/10 border border-alexa-accent/20'
                  }`}
                >
                  <p className="text-sm text-gray-200">{resp.text}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {resp.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-400 text-sm">Ask Sage about your sales pipeline</p>
              <p className="text-gray-500 text-xs mt-1">Click a suggestion or type a command</p>
            </div>
          )}
        </div>
      </div>

      {/* Voice Suggestions */}
      <div className="bg-alexa-card rounded-xl border border-alexa-accent/30 p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Try saying</h3>
        <div className="flex flex-wrap gap-2">
          {VOICE_SUGGESTIONS.map((suggestion, i) => (
            <button
              key={i}
              onClick={() => handleSuggestionClick(suggestion)}
              className="px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 hover:text-white transition-colors text-sm"
            >
              "{suggestion}"
            </button>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-alexa-card rounded-xl border border-alexa-accent/30 p-5">
        <form onSubmit={handleSubmit} className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleListening}
            className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isListening
                ? 'bg-red-500/20 border-2 border-red-500/50 text-red-400'
                : 'bg-alexa-blue/20 border-2 border-alexa-blue/50 text-alexa-blue hover:bg-alexa-blue/30'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </button>
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type a command or click the mic..."
            className="flex-1 bg-alexa-dark border border-alexa-accent/30 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-alexa-blue/50"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isProcessing}
            className="flex-shrink-0 px-6 py-3 bg-alexa-blue text-alexa-dark font-semibold rounded-lg hover:bg-alexa-blue/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Ask Sage
          </button>
        </form>
      </div>

      {/* Conversation History */}
      {responses.length > 0 && (
        <div className="bg-alexa-card rounded-xl border border-alexa-accent/30 p-5">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Conversation</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {responses.map((resp, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-alexa-blue/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-200">{resp.text}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {resp.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
