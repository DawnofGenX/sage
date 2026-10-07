// End-to-end tests for the Sage web simulator.
//
// These drive the REAL UI against a REAL backend. They are not mocks: the
// streaming assertions read the actual SSE bytes the backend emits on
// POST /api/stream/agentic_loop, and the UI assertions read what the browser
// rendered from those bytes.
//
// Prerequisites (both must already be running):
//   cd mcp-server    && .venv/bin/python -m uvicorn src.api.rest:app --port 8000
//   cd web-simulator && npm run dev            # serves on :3000, proxies /api -> :8000
//
// First run needs a browser binary:
//   npx playwright install chromium
//
// The previous version of this file referenced 'Start Demo' and
// 'Demo complete!', both removed when DemoMode became stream-driven; it could
// not run. The tests below target the current UI: the 'Extract Insights'
// button (disabled until a transcript is loaded) and the Demo Mode modal
// ('Agentic Chain Demo').

import { test, expect, Page } from '@playwright/test';

const BASE = 'http://localhost:3000';

// The backend's mock extractor only yields a full five-step success for a
// transcript that contains both a contact and a deal amount. The UI's built-in
// samples halt earlier (they carry no deal), so the success path uses the
// text-input fallback with an explicit transcript.
const SUCCESS_TRANSCRIPT =
  'Hi, this is Alex from Sage. John Smith at Acme Corp wants the enterprise ' +
  'plan, budget around $50,000. Sarah Chen is the VP of Engineering. ' +
  'Let us follow up on 12/15/2026.';

// No contact, no deal: the chain must halt honestly after one step.
const HALT_TRANSCRIPT = 'mm hm, sure, let us circle back';

/**
 * Force the VoiceInput text fallback.
 *
 * The component renders its microphone UI whenever `SpeechRecognition` (or the
 * webkit alias) exists on `window`, and headless Chromium defines both — so the
 * textarea never appears by default. Deleting the globals before the app boots
 * makes `'webkitSpeechRecognition' in window` false and the fallback render.
 */
async function useTextFallback(page: Page) {
  await page.addInitScript(() => {
    for (const key of ['SpeechRecognition', 'webkitSpeechRecognition']) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        delete (window as any)[key];
      } catch {
        /* non-configurable: the property is absent anyway on some engines */
      }
    }
  });
}

async function submitTranscriptAndExtract(page: Page, transcript: string): Promise<string> {
  const sseResponse = page.waitForResponse(
    (r) => r.url().includes('/api/stream/agentic_loop') && r.request().method() === 'POST',
  );
  await page.getByPlaceholder('Type or paste a call transcript here...').fill(transcript);
  await page.getByRole('button', { name: 'Submit Transcript' }).click();
  // The button is disabled until a transcript exists; the submit above enables it.
  await expect(page.getByRole('button', { name: 'Extract Insights' })).toBeEnabled();
  await page.getByRole('button', { name: 'Extract Insights' }).click();
  const response = await sseResponse;
  return response.text();
}

test('dashboard loads and reports backend health', async ({ page }) => {
  await page.goto('/');

  // The app shell renders.
  await expect(page.getByText('Sage').first()).toBeVisible();

  // The hero must not claim the backend is unreachable.
  await expect(page.getByText('Backend unreachable')).toHaveCount(0);

  // The dashboard pre-loads pipeline health and the daily briefing. If either
  // call failed, the app shows the "Some data failed to load" banner — its
  // absence is the signal that the backend answered.
  await expect(page.getByText('Extraction Pipeline')).toBeVisible();
  await expect(page.getByText('Some data failed to load')).toHaveCount(0);
});

test('agentic loop streams steps and completes with a real record id', async ({ page }) => {
  await useTextFallback(page);
  await page.goto('/');

  const sseBody = await submitTranscriptAndExtract(page, SUCCESS_TRANSCRIPT);

  // The backend emitted five step frames for this transcript.
  expect(sseBody.match(/event: step/g)?.length).toBe(5);

  // Each step frame carries a tool name and a provenance badge value.
  expect(sseBody).toContain('"tool": "extract_from_call"');
  expect(sseBody).toContain('"tool": "sync_to_crm"');
  expect(sseBody).toContain('"provenance": "mock"'); // extraction ran in mock mode
  expect(sseBody).toContain('"provenance": "local"'); // sync wrote to the local CRM

  // The run completed successfully with a real local-CRM record id.
  expect(sseBody).toContain('"status": "success"');
  expect(sseBody).toMatch(/loc_d_[0-9A-Z]{26}/);
  expect(sseBody).not.toContain('event: error');

  // The UI reflected the completion: the reasoning trace appeared and the
  // pipeline reached its complete state.
  await expect(page.getByText('Reasoning Trace')).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Complete').first()).toBeVisible({ timeout: 30000 });
});

test('Demo Mode streams the chain with provenance badges', async ({ page }) => {
  await page.goto('/');

  // DemoFlow fetches tool discovery on mount; capture that exact GET.
  const toolsResponse = page.waitForResponse(
    (r) => r.url().endsWith('/api/tools') && r.request().method() === 'GET',
  );
  await page.getByRole('button', { name: 'Demo Mode' }).click();

  // The modal loads tool discovery before it will run the chain.
  await expect(page.getByText('Agentic Chain Demo')).toBeVisible();
  await expect(page.getByText('tools available')).toBeVisible();

  // Tool discovery is live and returns the registered count (23).
  const tools = await (await toolsResponse).json();
  expect(tools.count).toBe(23);

  await page.getByRole('button', { name: 'Start Agentic Chain' }).click();

  // The first step arrives with its tool name and its provenance badge.
  await expect(page.getByText('extract_from_call')).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('mock', { exact: true })).toBeVisible({ timeout: 30000 });

  // The run terminates with an explicit, honest status line (the shipped demo
  // transcript halts at 'incomplete' because it yields no deal — the chain
  // never fabricates one).
  await expect(page.getByText(/Status: \w+/)).toBeVisible({ timeout: 30000 });
});

test('halt path is honest: incomplete with no fabricated record', async ({ page }) => {
  await useTextFallback(page);
  await page.goto('/');

  const sseBody = await submitTranscriptAndExtract(page, HALT_TRANSCRIPT);

  // Exactly one step ran (extract), then the chain halted.
  expect(sseBody.match(/event: step/g)?.length).toBe(1);
  expect(sseBody).toContain('"tool": "extract_from_call"');

  // A halted chain is a legitimate outcome, not an error.
  expect(sseBody).not.toContain('event: error');

  // The completion frame says so plainly and reports no record id.
  expect(sseBody).toContain('"status": "incomplete"');
  expect(sseBody).not.toMatch(/loc_d_[0-9A-Z]{26}/);

  // The UI did not crash and still rendered the dashboard.
  await expect(page.getByText('Extraction Pipeline')).toBeVisible({ timeout: 30000 });
});
