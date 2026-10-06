'use strict';

/**
 * Sage Alexa+ Skill
 *
 * A real Alexa Skills Kit skill that connects to the Sage MCP server
 * REST API to provide voice-activated sales intelligence.
 *
 * Environment variables:
 *   SAGE_MCP_URL  - Base URL of the Sage MCP server (default: http://localhost:8000)
 */

const axios = require('axios');
const {
  SkillBuilders,
  getRequestType,
  getIntentName,
  getSlotValue,
} = require('ask-sdk-core');

// ─── API Client ──────────────────────────────────────────────────────────────

const MCP_SERVER_URL = process.env.SAGE_MCP_URL || 'http://localhost:8000';

/**
 * Create an API client for the Sage MCP server.
 * Injectable for testing.
 */
function createApiClient(baseUrl = MCP_SERVER_URL) {
  const client = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
  });

  return {
    async getPipelineHealth() {
      const resp = await client.get('/api/tools/get_pipeline_health');
      return resp.data;
    },
    async getContactContext(name) {
      const resp = await client.post('/api/tools/get_contact_context', { name });
      return resp.data;
    },
    async getTodaysFollowups() {
      const resp = await client.get('/api/tools/get_todays_followups');
      return resp.data;
    },
  };
}

// Default client instance
const apiClient = createApiClient();

// ─── Speech Helpers ──────────────────────────────────────────────────────────

function formatCurrency(value) {
  if (value == null) return 'unknown';
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)} million`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)} thousand`;
  return `$${value}`;
}

function formatPipelineSummary(data) {
  const totalDeals = data.total_deals || 0;
  const totalValue = data.total_value || 0;
  const stages = data.deals_by_stage || {};
  const stuckDeals = data.stuck_deals || [];

  let summary = `You have ${totalDeals} deals in your pipeline worth ${formatCurrency(totalValue)}.`;

  const stageEntries = Object.entries(stages);
  if (stageEntries.length > 0) {
    const stageStr = stageEntries.map(([stage, count]) => `${count} in ${stage}`).join(', ');
    summary += ` Breakdown: ${stageStr}.`;
  }

  if (stuckDeals.length > 0) {
    summary += ` ${stuckDeals.length} deal${stuckDeals.length > 1 ? 's' : ''} may need attention.`;
  }

  return summary;
}

function formatContactSummary(data) {
  const contact = data.contact;
  if (!contact) {
    return 'I could not find that contact. Please try another name.';
  }

  const deals = data.deals || [];
  const activities = data.activities || [];
  const name = contact.name || 'Unknown';
  const company = contact.company || 'unknown company';
  const title = contact.title || '';

  let summary = `${name}`;
  if (title) summary += `, ${title}`;
  summary += ` at ${company}.`;

  if (deals.length > 0) {
    const dealValues = deals.map(d => d.value).filter(v => v != null);
    const totalValue = dealValues.reduce((a, b) => a + b, 0);
    summary += ` They have ${deals.length} deal${deals.length > 1 ? 's' : ''} worth ${formatCurrency(totalValue)}.`;
  }

  if (activities.length > 0) {
    summary += ` ${activities.length} recent activit${activities.length > 1 ? 'ies' : 'y'} on record.`;
  }

  return summary;
}

function formatFollowupsSummary(data) {
  const followups = data.followups || [];
  const total = data.total || followups.length;

  if (total === 0) {
    return 'You have no follow-ups due today. Great job staying on top of things!';
  }

  let summary = `You have ${total} follow-up${total > 1 ? 's' : ''} due today.`;

  const highPriority = followups.filter(f => f.priority === 'high');
  if (highPriority.length > 0) {
    summary += ` ${highPriority.length} high priority.`;
  }

  const first = followups[0];
  if (first) {
    const title = first.title || 'Follow-up';
    const due = first.due_date ? ` due ${first.due_date}` : '';
    summary += ` First up: ${title}${due}.`;
  }

  return summary;
}

// ─── Intent Handlers ─────────────────────────────────────────────────────────

const LaunchRequestHandler = {
  canHandle(handlerInput) {
    return getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
  },
  handle(handlerInput) {
    const speakOutput = [
      'Welcome to Sage, your passive sales intelligence assistant.',
      'I can help you check your pipeline, get contact context, and review follow-ups.',
      'Try saying: "What\'s my pipeline?", "Tell me about Sarah Chen", or "Any follow-ups due?"',
    ].join(' ');

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .reprompt('What would you like to know about your sales pipeline?')
      .getResponse();
  },
};

const PipelineIntentHandler = {
  canHandle(handlerInput) {
    return (
      getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      getIntentName(handlerInput.requestEnvelope) === 'PipelineIntent'
    );
  },
  async handle(handlerInput) {
    let speakOutput;
    try {
      const data = await apiClient.getPipelineHealth();
      speakOutput = formatPipelineSummary(data);
    } catch (error) {
      console.error('PipelineIntent error:', error.message);
      speakOutput = 'Sorry, I had trouble fetching your pipeline data. Please try again later.';
    }

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const ContactIntentHandler = {
  canHandle(handlerInput) {
    return (
      getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      getIntentName(handlerInput.requestEnvelope) === 'ContactIntent'
    );
  },
  async handle(handlerInput) {
    const contactName = getSlotValue(handlerInput.requestEnvelope, 'contactName');

    if (!contactName) {
      return handlerInput.responseBuilder
        .speak('Which contact would you like to know about?')
        .reprompt('Please tell me a contact name.')
        .getResponse();
    }

    let speakOutput;
    try {
      const data = await apiClient.getContactContext(contactName);
      speakOutput = formatContactSummary(data);
    } catch (error) {
      console.error('ContactIntent error:', error.message);
      speakOutput = `Sorry, I had trouble looking up ${contactName}. Please try again later.`;
    }

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const FollowUpIntentHandler = {
  canHandle(handlerInput) {
    return (
      getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      getIntentName(handlerInput.requestEnvelope) === 'FollowUpIntent'
    );
  },
  async handle(handlerInput) {
    let speakOutput;
    try {
      const data = await apiClient.getTodaysFollowups();
      speakOutput = formatFollowupsSummary(data);
    } catch (error) {
      console.error('FollowUpIntent error:', error.message);
      speakOutput = 'Sorry, I had trouble fetching your follow-ups. Please try again later.';
    }

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const HelpIntentHandler = {
  canHandle(handlerInput) {
    return (
      getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent'
    );
  },
  handle(handlerInput) {
    const speakOutput = [
      'Sage is your passive sales intelligence assistant.',
      'You can ask me:',
      '"What\'s my pipeline?" for a summary of your deals.',
      '"Tell me about" followed by a contact name for their context.',
      '"Any follow-ups due?" for today\'s prioritized follow-ups.',
      'What would you like to do?',
    ].join(' ');

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .reprompt('What would you like to know?')
      .getResponse();
  },
};

const CancelAndStopIntentHandler = {
  canHandle(handlerInput) {
    return (
      getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      (getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent' ||
        getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent')
    );
  },
  handle(handlerInput) {
    const speakOutput = 'Goodbye! Sage will keep listening for updates.';

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const ErrorHandler = {
  canHandle() {
    return true;
  },
  handle(handlerInput, error) {
    console.error('Skill error:', error.message);
    console.error('Stack:', error.stack);

    const speakOutput = 'Sorry, I had trouble understanding that. Please try again.';

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .reprompt('Please try again.')
      .getResponse();
  },
};

// ─── Skill Builder ───────────────────────────────────────────────────────────

function buildSkill(client = apiClient) {
  // Override the module-level client for this skill instance
  apiClient.getPipelineHealth = client.getPipelineHealth;
  apiClient.getContactContext = client.getContactContext;
  apiClient.getTodaysFollowups = client.getTodaysFollowups;

  return SkillBuilders.custom()
    .addRequestHandlers(
      LaunchRequestHandler,
      PipelineIntentHandler,
      ContactIntentHandler,
      FollowUpIntentHandler,
      HelpIntentHandler,
      CancelAndStopIntentHandler
    )
    .addErrorHandlers(ErrorHandler)
    .lambda();
}

// ─── Lambda Handler ──────────────────────────────────────────────────────────

exports.handler = buildSkill();

// ─── Exports for Testing ─────────────────────────────────────────────────────

module.exports = {
  handler: exports.handler,
  LaunchRequestHandler,
  PipelineIntentHandler,
  ContactIntentHandler,
  FollowUpIntentHandler,
  HelpIntentHandler,
  CancelAndStopIntentHandler,
  ErrorHandler,
  buildSkill,
  createApiClient,
  formatPipelineSummary,
  formatContactSummary,
  formatFollowupsSummary,
};
