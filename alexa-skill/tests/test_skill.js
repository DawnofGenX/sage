'use strict';

/**
 * Tests for Sage Alexa+ Skill
 *
 * Run with: npm test
 */

const assert = require('assert');
const {
  LaunchRequestHandler,
  PipelineIntentHandler,
  ContactIntentHandler,
  FollowUpIntentHandler,
  HelpIntentHandler,
  CancelAndStopIntentHandler,
  ErrorHandler,
  formatPipelineSummary,
  formatContactSummary,
  formatFollowupsSummary,
  createApiClient,
} = require('../index');

// ─── Test Helpers ────────────────────────────────────────────────────────────

function createMockHandlerInput(requestEnvelope) {
  return {
    requestEnvelope,
    responseBuilder: {
      _speech: '',
      _reprompt: '',
      speak(text) {
        this._speech = text;
        return this;
      },
      reprompt(text) {
        this._reprompt = text;
        return this;
      },
      getResponse() {
        return {
          outputSpeech: { text: this._speech },
          reprompt: { outputSpeech: { text: this._reprompt } },
        };
      },
    },
  };
}

function createLaunchRequest() {
  return {
    version: '1.0',
    session: { new: true },
    context: {},
    request: {
      type: 'LaunchRequest',
      requestId: 'test-launch',
      timestamp: new Date().toISOString(),
    },
  };
}

function createIntentRequest(intentName, slots = {}) {
  return {
    version: '1.0',
    session: { new: false },
    context: {},
    request: {
      type: 'IntentRequest',
      requestId: 'test-intent',
      timestamp: new Date().toISOString(),
      intent: {
        name: intentName,
        slots: Object.entries(slots).reduce((acc, [key, value]) => {
          acc[key] = { name: key, value };
          return acc;
        }, {}),
      },
    },
  };
}

// ─── Mock API Client ─────────────────────────────────────────────────────────

function createMockClient(overrides = {}) {
  return {
    getPipelineHealth: async () => ({
      total_deals: 5,
      total_value: 470000,
      deals_by_stage: { lead: 2, proposal: 1, negotiation: 1, closed_won: 1 },
      stuck_deals: [{ id: 2, title: 'Globex Platform Deal' }],
    }),
    getContactContext: async (name) => ({
      contact: { name, company: 'Acme Corp', title: 'VP of Engineering' },
      deals: [{ title: 'Acme Enterprise License', value: 50000, stage: 'proposal' }],
      activities: [{ type: 'call', description: 'Follow-up call' }],
    }),
    getTodaysFollowups: async () => ({
      followups: [
        { title: 'Schedule demo', due_date: 'Next Tuesday', priority: 'high' },
        { title: 'Follow up on conversation', due_date: 'Friday', priority: 'medium' },
      ],
      total: 2,
    }),
    ...overrides,
  };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    const result = fn();
    if (result && typeof result.then === 'function') {
      return result
        .then(() => {
          console.log(`  ✓ ${name}`);
          passed++;
        })
        .catch((err) => {
          console.error(`  ✗ ${name}`);
          console.error(`    ${err.message}`);
          failed++;
        });
    }
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
  return Promise.resolve();
}

async function runTests() {
  console.log('\nSage Alexa+ Skill Tests\n');

  // ── Launch Request ────────────────────────────────────────────────────────

  await test('LaunchRequestHandler returns welcome message', async () => {
    const handlerInput = createMockHandlerInput(createLaunchRequest());
    const response = LaunchRequestHandler.handle(handlerInput);
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('Welcome to Sage'),
      'Should welcome user'
    );
    assert(
      response.outputSpeech.text.includes('pipeline'),
      'Should mention pipeline'
    );
  });

  await test('LaunchRequestHandler canHandle detects LaunchRequest', () => {
    const handlerInput = createMockHandlerInput(createLaunchRequest());
    assert(
      LaunchRequestHandler.canHandle(handlerInput),
      'Should handle LaunchRequest'
    );
  });

  // ── Pipeline Intent ───────────────────────────────────────────────────────

  await test('PipelineIntentHandler calls API and speaks summary', async () => {
    const mockClient = createMockClient();
    let apiCalled = false;
    const origGet = mockClient.getPipelineHealth;
    mockClient.getPipelineHealth = async () => {
      apiCalled = true;
      return origGet();
    };

    // Temporarily override the module's apiClient
    const mod = require('../index');
    const origClient = mod.createApiClient;
    // We need to inject the mock - use a different approach
    // The handler uses the module-level apiClient, so we test via formatPipelineSummary

    const handlerInput = createMockHandlerInput(createIntentRequest('PipelineIntent'));

    // Mock the API by temporarily replacing axios
    const axios = require('axios');
    const origCreate = axios.create;
    axios.create = () => ({
      get: async (url) => {
        assert(url.includes('get_pipeline_health'), 'Should call pipeline health endpoint');
        apiCalled = true;
        return { data: await mockClient.getPipelineHealth() };
      },
      post: async (url, data) => ({ data: {} }),
    });

    // Re-require to get fresh module with mocked axios
    delete require.cache[require.resolve('../index')];
    const freshMod = require('../index');
    const response = await freshMod.PipelineIntentHandler.handle(handlerInput);

    axios.create = origCreate;
    delete require.cache[require.resolve('../index')];

    assert(apiCalled, 'API should have been called');
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('5 deals'),
      'Should mention deal count'
    );
  });

  await test('PipelineIntentHandler handles API errors gracefully', async () => {
    const axios = require('axios');
    const origCreate = axios.create;
    axios.create = () => ({
      get: async () => {
        throw new Error('Network error');
      },
      post: async () => ({ data: {} }),
    });

    delete require.cache[require.resolve('../index')];
    const freshMod = require('../index');
    const handlerInput = createMockHandlerInput(createIntentRequest('PipelineIntent'));
    const response = await freshMod.PipelineIntentHandler.handle(handlerInput);

    axios.create = origCreate;
    delete require.cache[require.resolve('../index')];

    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('trouble'),
      'Should handle error gracefully'
    );
  });

  // ── Contact Intent ────────────────────────────────────────────────────────

  await test('ContactIntentHandler calls API with contact name', async () => {
    const axios = require('axios');
    let capturedName = null;
    const origCreate = axios.create;
    axios.create = () => ({
      get: async () => ({ data: {} }),
      post: async (url, data) => {
        assert(url.includes('get_contact_context'), 'Should call contact context endpoint');
        capturedName = data.name;
        return {
          data: {
            contact: { name: data.name, company: 'Acme Corp', title: 'VP of Engineering' },
            deals: [{ title: 'Acme Enterprise License', value: 50000, stage: 'proposal' }],
            activities: [{ type: 'call', description: 'Follow-up call' }],
          },
        };
      },
    });

    delete require.cache[require.resolve('../index')];
    const freshMod = require('../index');
    const handlerInput = createMockHandlerInput(
      createIntentRequest('ContactIntent', { contactName: 'Sarah Chen' })
    );
    const response = await freshMod.ContactIntentHandler.handle(handlerInput);

    axios.create = origCreate;
    delete require.cache[require.resolve('../index')];

    assert.strictEqual(capturedName, 'Sarah Chen', 'Should pass contact name to API');
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('Sarah Chen'),
      'Should mention contact name'
    );
  });

  await test('ContactIntentHandler prompts for name when slot is empty', async () => {
    const handlerInput = createMockHandlerInput(createIntentRequest('ContactIntent'));
    const response = await ContactIntentHandler.handle(handlerInput);
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('Which contact'),
      'Should ask for contact name'
    );
  });

  // ── FollowUp Intent ───────────────────────────────────────────────────────

  await test('FollowUpIntentHandler calls API and speaks follow-ups', async () => {
    const axios = require('axios');
    let apiCalled = false;
    const origCreate = axios.create;
    axios.create = () => ({
      get: async (url) => {
        if (url.includes('get_todays_followups')) {
          apiCalled = true;
          return {
            data: {
              followups: [
                { title: 'Schedule demo', due_date: 'Next Tuesday', priority: 'high' },
              ],
              total: 1,
            },
          };
        }
        return { data: {} };
      },
      post: async () => ({ data: {} }),
    });

    delete require.cache[require.resolve('../index')];
    const freshMod = require('../index');
    const handlerInput = createMockHandlerInput(createIntentRequest('FollowUpIntent'));
    const response = await freshMod.FollowUpIntentHandler.handle(handlerInput);

    axios.create = origCreate;
    delete require.cache[require.resolve('../index')];

    assert(apiCalled, 'API should have been called');
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('follow-up'),
      'Should mention follow-ups'
    );
  });

  // ── Help Intent ───────────────────────────────────────────────────────────

  await test('HelpIntentHandler explains capabilities', () => {
    const handlerInput = createMockHandlerInput(createIntentRequest('AMAZON.HelpIntent'));
    const response = HelpIntentHandler.handle(handlerInput);
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('pipeline'),
      'Should mention pipeline capability'
    );
    assert(
      response.outputSpeech.text.includes('contact'),
      'Should mention contact capability'
    );
  });

  // ── Cancel/Stop Intent ────────────────────────────────────────────────────

  await test('CancelAndStopIntentHandler says goodbye', () => {
    const handlerInput = createMockHandlerInput(createIntentRequest('AMAZON.StopIntent'));
    const response = CancelAndStopIntentHandler.handle(handlerInput);
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('Goodbye'),
      'Should say goodbye'
    );
  });

  // ── Error Handler ─────────────────────────────────────────────────────────

  await test('ErrorHandler handles errors gracefully', () => {
    const handlerInput = createMockHandlerInput(createIntentRequest('UnknownIntent'));
    const response = ErrorHandler.handle(handlerInput, new Error('Test error'));
    assert(response.outputSpeech, 'Response should have outputSpeech');
    assert(
      response.outputSpeech.text.includes('trouble'),
      'Should give graceful error message'
    );
  });

  await test('ErrorHandler canHandle returns true for any input', () => {
    const handlerInput = createMockHandlerInput(createIntentRequest('AnyIntent'));
    assert(ErrorHandler.canHandle(handlerInput), 'Should handle any input');
  });

  // ── Format Helpers ────────────────────────────────────────────────────────

  await test('formatPipelineSummary formats correctly', () => {
    const data = {
      total_deals: 5,
      total_value: 470000,
      deals_by_stage: { lead: 2, proposal: 1 },
      stuck_deals: [{ id: 1 }],
    };
    const summary = formatPipelineSummary(data);
    assert(summary.includes('5 deals'), 'Should include deal count');
    assert(summary.includes('$470,000') || summary.includes('470 thousand'), 'Should include value');
  });

  await test('formatContactSummary handles missing contact', () => {
    const summary = formatContactSummary({ contact: null, deals: [], activities: [] });
    assert(summary.includes('could not find'), 'Should handle missing contact');
  });

  await test('formatFollowupsSummary handles empty list', () => {
    const summary = formatFollowupsSummary({ followups: [], total: 0 });
    assert(summary.includes('no follow-ups'), 'Should handle empty follow-ups');
  });

  // ── API Client ────────────────────────────────────────────────────────────

  await test('createApiClient uses SAGE_MCP_URL env var', () => {
    const origUrl = process.env.SAGE_MCP_URL;
    process.env.SAGE_MCP_URL = 'http://test-server:9000';
    const client = createApiClient(process.env.SAGE_MCP_URL);
    assert(client, 'Should create client');
    assert(client.getPipelineHealth, 'Should have getPipelineHealth method');
    assert(client.getContactContext, 'Should have getContactContext method');
    assert(client.getTodaysFollowups, 'Should have getTodaysFollowups method');
    if (origUrl) {
      process.env.SAGE_MCP_URL = origUrl;
    } else {
      delete process.env.SAGE_MCP_URL;
    }
  });

  // ── Results ───────────────────────────────────────────────────────────────

  console.log(`\nResults: ${passed} passed, ${failed} failed\n`);
  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Test runner error:', err);
  process.exit(1);
});
