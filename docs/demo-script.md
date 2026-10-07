# Sage Demo Script (60 Seconds)

**Target length:** 60 seconds  
**Resolution:** 1920×1080 (1080p)  
**Format:** MP4, 30 fps, H.264

---

## Segment 1: The Problem [0:00 – 0:10]

**Visual:** Split screen — left side shows a salesperson on a call (stock photo or illustration), right side shows manual CRM data entry in Salesforce/HubSpot. Fade between the two to emphasize the friction.

**On-screen text:**
- "2+ hours/day on data entry"
- "Deals fall through the cracks"
- "Follow-ups get forgotten"

**Voiceover:**
> "Salespeople spend over two hours a day on CRM data entry. Deals fall through the cracks. Follow-ups get forgotten."

**UI elements to reference:**
- Stock photo: salesperson on phone (Pexels/Unsplash)
- Stock photo: CRM interface with manual form filling
- Text overlay with animated counter: "2.1 hrs/day"

---

## Segment 2: Passive Listening [0:10 – 0:25]

**Visual:** Transition to the Sage web simulator. Show the VoiceInput component with the microphone active. The TranscriptView fills with a sample call transcript in real-time. The "Load Sample Call" dropdown is visible in the header.

**On-screen text:**
- "No wake words. No commands."
- "Just have the conversation."
- "Call in progress..."

**Voiceover:**
> "Sage listens passively. No wake words, no commands. Just have the conversation."

**UI elements to reference:**
- **Header:** "Load Sample Call" dropdown button (top-right)
- **VoiceInput component:** Mic icon pulsing/active state, "Listening..." indicator
- **TranscriptView component:** Live transcript text appearing line by line
- **Call timer:** Elapsed time counter in TranscriptView

**Action:** Click "Load Sample Call" → select a sample → transcript populates → click "Start Listening" to show active state.

---

## Segment 3: Auto-Extraction [0:25 – 0:40]

**Visual:** The ExtractionPipeline component runs through all 4 stages (2 LLM passes + local validation). Each stage animates from "pending" → "running" → "complete" with checkmarks. The ReasoningTrace panel below shows the 7-step internal trace. Real LLM extraction is happening (Amazon Nova via AWS Bedrock).

**On-screen text:**
- "Extracting insights..."
- "Amazon Nova via AWS Bedrock"
- Step labels: "Entity Extraction" → "Intent Classification" → "Record Generation" → "Schema Validation (local)"

**Voiceover:**
> "After the call, Sage extracts everything using Amazon Nova: contacts, deals, follow-ups, sentiment, buying signals."

**UI elements to reference:**
- **ExtractionPipeline component:** 4 stages with animated progress (2 LLM passes + local validation)
  - Stage 1: Entity Extraction — "Extract people, companies, amounts, dates" (LLM pass 1)
  - Stage 2: Intent Classification — "Classify call intent and purpose" (LLM pass 1)
  - Stage 3: Record Generation — "Generate CRM records from transcript" (LLM pass 2)
  - Stage 4: Schema Validation — "Validate and normalize extracted data" (local, no LLM)
- **ReasoningTrace component:** 7-step internal trace (Tokenize → NER → Intent → Record → Validate → Deduplicate → Write)
- **Extract Insights button:** Shows spinner + "Processing..." during extraction

**Action:** Click "Extract Insights" button → watch all 4 pipeline stages complete → extraction result panel appears with structured data.

---

## Segment 4: Proactive Insight [0:40 – 0:50]

**Visual:** The ProactiveInsights component displays urgency-coded insight cards. Cards are color-coded: red for overdue, amber for stuck, blue for info. The top card highlights the Acme follow-up. The "Generate Insights" button triggers a refresh animation.

**On-screen text:**
- "You haven't followed up with Acme in 20 days."
- "Their Q4 budget deadline is Friday."
- "3 deals need attention"

**Voiceover:**
> "And Sage doesn't wait for you to ask. It proactively tells you what you're forgetting."

**UI elements to reference:**
- **ProactiveInsights component:** Insight cards with urgency badges
  - Overdue card (red): "Overdue follow-up: Schedule demo with Sarah Chen"
  - Stuck card (amber): "Stuck deal: Globex Platform Deal — no activity for 16 days"
  - Info card (blue): "Budget deadline approaching: Acme Enterprise License"
- **Urgency indicators:** Color-coded left borders + badge labels
- **"Generate Insights" button:** Triggers insight refresh animation

**Action:** Click "Generate Insights" → new insight cards animate in → highlight the Acme overdue card.

---

## Segment 5: CRM Sync + Close [0:50 – 1:00]

**Visual:** The PipelineBoard component shows a Kanban board with deals across stages. Click "Sync to CRM" → sync animation plays → "Sync Complete" toast appears. Then show the Alexa+ view with the morning briefing on an Echo Show simulation. End with the hero section and GitHub link.

**On-screen text:**
- "Synced to Salesforce ✓"
- "Sage. Your CRM that listens."
- "github.com/yourusername/sage"
- "Built for Amazon Developer Hackathon 2026"

**Voiceover:**
> "Everything synced to your CRM automatically. Sage. Your CRM that listens."

**UI elements to reference:**
- **PipelineBoard component:** Kanban columns (Lead, Qualified, Proposal, Negotiation, Closed Won)
  - Deal cards with contact names, values, sentiment indicators
  - "Sync to CRM" button with loading spinner
  - "Sync Complete" toast notification (green, bottom-right)
- **AlexaView component:** Echo Show simulation with morning briefing card
  - Greeting: "Good morning, here's your pipeline update"
  - Insight cards rendered as Alexa+ cards
  - Pipeline health summary
- **Hero section:** "Sage — Your CRM that listens" with stats (2.5 hrs saved, 0 manual entries)
- **End card:** GitHub repo URL + hackathon badge

**Action:** Click "Sync to CRM" → sync animation → toast appears → switch to Alexa+ tab → show briefing → fade to end card with repo URL.

---

## Full Voiceover Script (Continuous)

```
[0:00] Salespeople spend over two hours a day on CRM data entry.
        Deals fall through the cracks. Follow-ups get forgotten.

[0:10] Sage listens passively. No wake words, no commands.
        Just have the conversation.

[0:25] After the call, Sage extracts everything using Amazon Nova:
        contacts, deals, follow-ups, sentiment, buying signals.

[0:40] And Sage doesn't wait for you to ask.
        It proactively tells you what you're forgetting.

[0:50] Everything synced to your CRM automatically.
        Sage. Your CRM that listens.
```

**Delivery notes:**
- Pause 1 second between segments
- Emphasize: "passively", "everything", "proactively", "automatically"
- Keep energy up but conversational — confident, not salesy
- Smile while recording — it changes your tone

---

## Music Cues

| Segment | Music Mood | Notes |
|---------|-----------|-------|
| 0:00–0:10 | Tense, problem-focused | Low, slightly anxious tone |
| 0:10–0:25 | Curious, welcoming | Uplifting transition |
| 0:25–0:40 | Technical, precise | Subtle, methodical beat |
| 0:40–0:50 | Warm, helpful | Friendly, proactive feel |
| 0:50–1:00 | Triumphant, resolved | Confident closing |

**Source:** YouTube Audio Library (free, no copyright issues)  
**Ducking:** -20 dB under voiceover
