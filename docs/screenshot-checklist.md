# Screenshot Checklist

All screenshots should be captured at **1920×1080** resolution for consistency. Use browser DevTools (F12) → Device Toolbar → set to 1920×1080 if needed.

**Save all screenshots to:** `screenshots/` directory in the project root

---

## Screenshot 1: Main Dashboard with Hero Section

**What to capture:** Full web simulator dashboard with the Hero section visible at top, showing all major components below it.

**How:**
1. Open `http://localhost:3000` in Chrome
2. Ensure you're on the "Dashboard" tab (default)
3. Wait for all data to load (loading skeletons disappear)
4. The Hero section should show: "Sage — Your CRM that listens" with stats (2.5 hrs saved, 0 manual entries)
5. Capture the full page or ensure Hero + all components are visible
6. Save as: `screenshots/01-dashboard-hero.png`

**Checklist:**
- [ ] Hero section visible with tagline "Your CRM that listens"
- [ ] Hero stats visible (hours saved, manual entries)
- [ ] VoiceInput component visible
- [ ] TranscriptView component visible
- [ ] ExtractionPipeline component visible
- [ ] ProactiveInsights component visible
- [ ] PipelineBoard component visible
- [ ] No overlapping or cut-off elements
- [ ] No browser UI (address bar, tabs) in screenshot
- [ ] Clean, professional appearance

---

## Screenshot 2: Auto-Demo Mode Running

**What to capture:** The Demo Mode modal running through the automated demo flow.

**How:**
1. Open web simulator
2. Click "Demo Mode" button in header (purple button, top-right)
3. The DemoMode modal opens and starts running through scenarios
4. Capture mid-demo — show the modal with progress indicators
5. Save as: `screenshots/02-auto-demo-mode.png`

**Checklist:**
- [ ] Demo Mode modal visible
- [ ] Progress indicators/steps visible
- [ ] Current step highlighted
- [ ] Modal overlay on top of dashboard
- [ ] Clean, focused view

---

## Screenshot 3: Extraction Pipeline in Action

**What to capture:** ExtractionPipeline component with steps completing, showing the 4-step process.

**How:**
1. Load a sample call first (click "Load Sample Call" → select one)
2. Click "Extract Insights" button
3. Capture mid-pipeline — some steps complete, some in progress
4. Ideally show 2-3 steps with checkmarks and 1-2 steps animating
5. Also capture the ReasoningTrace panel below if visible
6. Save as: `screenshots/03-extraction-pipeline.png`

**Checklist:**
- [ ] All 4 steps visible: Entity Extraction, Intent Classification, Structured Record, Schema Validation
- [ ] At least one step shows a checkmark (complete)
- [ ] At least one step shows progress indicator (in progress)
- [ ] Step descriptions readable
- [ ] ReasoningTrace panel visible (7 steps)
- [ ] "Extract Insights" button shows "Processing..." state

---

## Screenshot 4: Proactive Insights with Urgency Cards

**What to capture:** ProactiveInsights component with multiple insight cards showing different urgency levels.

**How:**
1. Ensure insights are populated (run extraction first, or wait for auto-load)
2. If no insights, click "Generate Insights" button
3. Capture the ProactiveInsights component showing multiple cards
4. Ideally show different urgency levels (overdue/red, stuck/amber, info/blue)
5. Save as: `screenshots/04-proactive-insights.png`

**Checklist:**
- [ ] Multiple insight cards visible (at least 3)
- [ ] Urgency coding visible (color-coded borders or badges)
- [ ] At least one "overdue" card visible (red)
- [ ] At least one "stuck" card visible (amber)
- [ ] At least one "info" card visible (blue)
- [ ] Insight text readable
- [ ] Timestamps visible on cards

---

## Screenshot 5: Pipeline Board (Kanban)

**What to capture:** PipelineBoard component with Kanban columns and deal cards.

**How:**
1. Scroll to PipelineBoard component on the dashboard
2. Capture all columns: Lead, Qualified, Proposal, Negotiation, Closed Won
3. Ensure deal cards are visible in multiple columns
4. Save as: `screenshots/05-pipeline-board.png`

**Checklist:**
- [ ] All Kanban columns visible (Lead, Qualified, Proposal, Negotiation, Closed Won)
- [ ] Deal cards visible in multiple columns
- [ ] Deal values and contact names readable
- [ ] Sentiment indicators visible on cards
- [ ] "Sync to CRM" button visible
- [ ] Stuck deal indicators visible (if any)

---

## Screenshot 6: Alexa+ View (Echo Show Simulation)

**What to capture:** The Alexa+ tab showing the Echo Show simulation with morning briefing.

**How:**
1. Click "Alexa+" tab in the navigation bar
2. The AlexaView component renders an Echo Show simulation
3. Show the morning briefing card with pipeline update
4. Save as: `screenshots/06-alexa-view.png`

**Checklist:**
- [ ] Echo Show frame/bezel visible
- [ ] Morning briefing card visible
- [ ] Greeting text visible ("Good morning...")
- [ ] Insight cards rendered as Alexa+ cards
- [ ] Pipeline health summary visible
- [ ] Clean, realistic Echo Show appearance

---

## Screenshot 7: Call Simulator with Live Transcript

**What to capture:** The Call Simulator tab with a live or completed call transcript.

**How:**
1. Click "Call Sim" tab in the navigation bar
2. The CallSimulator component loads
3. Start a call simulation or load a sample
4. Capture with transcript visible and call in progress (or just completed)
5. Save as: `screenshots/07-call-simulator.png`

**Checklist:**
- [ ] Call simulator interface visible
- [ ] Transcript text visible
- [ ] Call timer or duration visible
- [ ] Microphone/call controls visible
- [ ] Contact information visible
- [ ] Clean, focused view

---

## Screenshot 8: Forecast Chart

**What to capture:** The Forecast tab showing the pipeline forecast chart.

**How:**
1. Click "Forecast" tab in the navigation bar
2. The ForecastChart component renders
3. Capture the full chart with data
4. Save as: `screenshots/08-forecast-chart.png`

**Checklist:**
- [ ] Chart visible with data
- [ ] X and Y axes labeled
- [ ] Multiple data series visible (if applicable)
- [ ] Legend visible
- [ ] Clean, readable chart
- [ ] No overlapping elements

---

## Screenshot 9: Activity Feed

**What to capture:** The Activity tab showing the activity feed with recent interactions.

**How:**
1. Click "Activity" tab in the navigation bar
2. The ActivityFeed component renders
3. Capture the full feed with multiple activity items
4. Save as: `screenshots/09-activity-feed.png`

**Checklist:**
- [ ] Multiple activity items visible
- [ ] Activity types distinguishable (call, email, meeting, task)
- [ ] Timestamps visible
- [ ] Contact/deal references visible
- [ ] Clean, chronological layout
- [ ] Icons or indicators for activity types

---

## Screenshot 10: Architecture Diagram

**What to capture:** System architecture diagram from architecture.md or README.md.

**How:**
1. Open `docs/architecture.md` in a markdown viewer that renders diagrams (e.g., VS Code with Markdown Preview, or GitHub)
2. Or open the README.md on GitHub and scroll to the architecture section
3. Capture the full architecture diagram
4. Save as: `screenshots/10-architecture.png`

**Checklist:**
- [ ] Full diagram visible (may need full-page capture)
- [ ] All components labeled: Alexa/Echo, Web Simulator, External CRM, MCP Server, SQLite DB
- [ ] Data flow arrows visible
- [ ] Text readable at 100% zoom
- [ ] Clean, professional rendering

---

## General Screenshot Tips

- **Use a clean browser profile** — no bookmarks bar, no extensions
- **Hide cursor** before capturing (or use a tool that excludes it)
- **Consistent naming:** `01-description.png`, `02-description.png`, etc.
- **Format:** PNG for UI screenshots
- **Storage:** Save to `screenshots/` directory in the project root
- **Git:** Add screenshots to the repo for Hackster.io image gallery
- **Resolution:** 1920×1080 for all screenshots
- **No sensitive data:** Ensure no API keys, personal data, or credentials are visible

## Post-Capture Checklist

- [ ] All 10 screenshots captured
- [ ] All screenshots are 1920×1080 (or full-page captures)
- [ ] No sensitive information visible (API keys, personal data, etc.)
- [ ] All text is readable
- [ ] Screenshots saved to `screenshots/` directory
- [ ] Screenshots added to git and pushed to GitHub
- [ ] Screenshots organized for Hackster.io image gallery upload
