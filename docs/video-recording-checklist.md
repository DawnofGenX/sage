# Sage Demo Video — Recording Checklist

**Use this checklist alongside `docs/demo-script.md` during recording.**

---

## 1. OBS Studio Setup

### Installation
- [ ] Download OBS Studio from https://obsproject.com/ (free, cross-platform)
- [ ] Install and launch OBS Studio
- [ ] Run Auto-Configuration Wizard (Tools → Auto-Configuration Wizard)

### Scene Collection
Create these scenes in the Scene Collection:

| Scene Name | Purpose | Sources |
|------------|---------|---------|
| `Intro` | Title card / problem statement | Text + background image |
| `Simulator` | Main web simulator recording | Display Capture (browser) |
| `Code` | Code/terminal view | Display Capture (VS Code) |
| `Architecture` | Architecture diagram | Display Capture (markdown viewer) |
| `EndCard` | GitHub link + hackathon badge | Text + background |

### Source Configuration

**Scene: Simulator**
- [ ] Add Source → Display Capture → select monitor
- [ ] Crop to browser window: right-click → Transform → Edit Transform → crop to 1920×1080
- [ ] Set browser zoom to 100%
- [ ] Use clean Chrome profile (no bookmarks bar, no extensions)
- [ ] Window size: exactly 1920×1080

**Scene: Intro**
- [ ] Add Source → Image → select problem-themed stock photo
- [ ] Add Source → Text (GDI+) → "2+ hours/day on data entry"
- [ ] Add Source → Text (GDI+) → "Deals fall through the cracks"

**Scene: EndCard**
- [ ] Add Source → Color Source → dark background (#0f172a or similar)
- [ ] Add Source → Text (GDI+) → "Sage. Your CRM that listens."
- [ ] Add Source → Text (GDI+) → "github.com/yourusername/sage"
- [ ] Add Source → Text (GDI+) → "Built for Amazon Developer Hackathon 2026"

### Audio Setup
- [ ] Add Source → Audio Input Capture → select USB microphone
- [ ] Recommended mics: Blue Yeti, Audio-Technica AT2020, Rode NT-USB
- [ ] Test mic levels: speak normally, verify peaks at -12 dB to -6 dB
- [ ] Disable desktop audio (we'll add background music in post)
- [ ] Add noise suppression filter: right-click mic source → Filters → Noise Suppression (RNNoise)

### Recording Settings
- [ ] Settings → Output → Recording → Type: Standard
- [ ] Recording Format: MP4
- [ ] Video Bitrate: 8000 Kbps
- [ ] Audio Bitrate: 160 kbps
- [ ] Encoder: x264 (or NVENC if available)
- [ ] Settings → Video → Base Resolution: 1920×1080
- [ ] Settings → Video → Output Resolution: 1920×1080
- [ ] Settings → Video → FPS: 30

---

## 2. Pre-Recording Checklist

### Environment
- [ ] Close all unnecessary applications (Slack, email, etc.)
- [ ] Enable Do Not Disturb / Focus Mode
- [ ] Disable desktop notifications
- [ ] Clear browser cache and cookies
- [ ] Set desktop wallpaper to solid color (clean background)

### Application Setup
- [ ] Start the MCP server: `cd mcp-server && python -m uvicorn src.api.rest:app --port 8000`
- [ ] Start the web simulator: `cd web-simulator && npm run dev`
- [ ] Verify simulator loads at `http://localhost:3000`
- [ ] Verify API health: `curl http://localhost:8000/api/health` → `{"status":"ok"}`
- [ ] Seed the database: `cd mcp-server && python -m src.data.seed`
- [ ] Open simulator in Chrome at exactly 1920×1080
- [ ] Set browser zoom to 100%
- [ ] Hide bookmarks bar (Ctrl+Shift+B)
- [ ] Use incognito/clean profile if possible

### OBS Verification
- [ ] Record 5-second test clip
- [ ] Verify video is 1920×1080, 30 fps
- [ ] Verify audio levels are good (peaks at -12 to -6 dB)
- [ ] Verify no audio/video sync issues
- [ ] Verify scene transitions work
- [ ] Check that browser UI (address bar, tabs) is not visible

### Voiceover Prep
- [ ] Print or display the voiceover script (from demo-script.md)
- [ ] Do vocal warm-up (humming, tongue twisters)
- [ ] Have water nearby
- [ ] Record in a quiet room with minimal echo
- [ ] Test record 10 seconds and playback to verify quality

---

## 3. Recording Steps

Record each segment as a separate take. You can stop and restart between segments.

### Segment 1: The Problem [0:00 – 0:10]
- [ ] Switch to `Intro` scene
- [ ] Start recording
- [ ] Show split screen: salesperson on call vs. manual CRM entry
- [ ] Display text overlay: "2+ hours/day on data entry"
- [ ] Record voiceover: "Salespeople spend over two hours a day on CRM data entry. Deals fall through the cracks. Follow-ups get forgotten."
- [ ] Stop recording
- [ ] Save take as: `takes/segment-1-problem.mp4`

### Segment 2: Passive Listening [0:10 – 0:25]
- [ ] Switch to `Simulator` scene
- [ ] Start recording
- [ ] Click "Load Sample Call" dropdown in header
- [ ] Select a sample call (e.g., "Acme Enterprise License")
- [ ] Show transcript populating in TranscriptView
- [ ] Click "Start Listening" to show active mic state
- [ ] Show live transcript appearing in real-time
- [ ] Display text overlay: "No wake words. No commands."
- [ ] Record voiceover: "Sage listens passively. No wake words, no commands. Just have the conversation."
- [ ] Stop recording
- [ ] Save take as: `takes/segment-2-listening.mp4`

### Segment 3: Auto-Extraction [0:25 – 0:40]
- [ ] Switch to `Simulator` scene
- [ ] Start recording
- [ ] Click "Extract Insights" button
- [ ] Show ExtractionPipeline running through all 4 stages (2 LLM passes + local validation):
  - [ ] Step 1: Entity Extraction (running → complete)
  - [ ] Step 2: Intent Classification (running → complete)
  - [ ] Step 3: Record Generation (running → complete)
  - [ ] Step 4: Schema Validation (running → complete)
- [ ] Show ReasoningTrace panel with 7-step internal trace
- [ ] Show extraction result with structured data
- [ ] Display text overlay: "Amazon Nova via AWS Bedrock"
- [ ] Record voiceover: "After the call, Sage extracts everything using Amazon Nova: contacts, deals, follow-ups, sentiment, buying signals."
- [ ] Stop recording
- [ ] Save take as: `takes/segment-3-extraction.mp4`

### Segment 4: Proactive Insight [0:40 – 0:50]
- [ ] Switch to `Simulator` scene
- [ ] Start recording
- [ ] Show ProactiveInsights component with insight cards
- [ ] Click "Generate Insights" to trigger refresh
- [ ] Show urgency-coded cards animating in:
  - [ ] Red/overdue card: "Overdue follow-up: Schedule demo with Sarah Chen"
  - [ ] Amber/stuck card: "Stuck deal: Globex Platform Deal"
  - [ ] Blue/info card: "Budget deadline approaching: Acme Enterprise License"
- [ ] Highlight the Acme insight card
- [ ] Display text overlay: "You haven't followed up with Acme in 20 days."
- [ ] Record voiceover: "And Sage doesn't wait for you to ask. It proactively tells you what you're forgetting."
- [ ] Stop recording
- [ ] Save take as: `takes/segment-4-insights.mp4`

### Segment 5: CRM Sync + Close [0:50 – 1:00]
- [ ] Switch to `Simulator` scene
- [ ] Start recording
- [ ] Show PipelineBoard with Kanban columns
- [ ] Click "Sync to CRM" button
- [ ] Show sync animation (spinner)
- [ ] Show "Sync Complete" toast notification
- [ ] Switch to Alexa+ tab
- [ ] Show AlexaView with morning briefing on Echo Show simulation
- [ ] Switch to `EndCard` scene
- [ ] Display: "Sage. Your CRM that listens." + GitHub URL + hackathon badge
- [ ] Record voiceover: "Everything synced to your CRM automatically. Sage. Your CRM that listens."
- [ ] Stop recording
- [ ] Save take as: `takes/segment-5-sync-close.mp4`

---

## 4. Post-Recording Steps

### Review
- [ ] Review all 5 takes
- [ ] Pick the best take for each segment
- [ ] Note timestamps of best takes for editing
- [ ] Discard bad takes

### Editing (DaVinci Resolve — Free)
- [ ] Import all best takes into Media Pool
- [ ] Create new timeline: 1920×1080, 30 fps
- [ ] Assemble segments in order on Video Track 1
- [ ] Add B-roll on Video Track 2 (stock photos for Segment 1)
- [ ] Add text overlays (Fusion → Text+):
  - [ ] "2+ hours/day on data entry" — Segment 1
  - [ ] "No wake words. No commands." — Segment 2
  - [ ] "Amazon Nova via AWS Bedrock" — Segment 3
  - [ ] "You haven't followed up with Acme in 20 days." — Segment 4
  - [ ] "Synced to Salesforce ✓" — Segment 5
  - [ ] End card with repo URL
- [ ] Add voiceover on Audio Track 1
- [ ] Add background music on Audio Track 2 (YouTube Audio Library)
- [ ] Duck music to -20 dB under voiceover
- [ ] Add cross-dissolve transitions between segments (0.5 seconds)
- [ ] Color correction: slight brightness/contrast boost for screen recordings

### Export
- [ ] File → Export → Render
- [ ] Format: MP4
- [ ] Codec: H.264
- [ ] Resolution: 1920×1080
- [ ] Frame rate: 30 fps
- [ ] Quality: Automatic (or restrict to 8000 Kbps)
- [ ] Audio: AAC, 48 kHz, 160 kbps
- [ ] Filename: `sage-demo-video.mp4`

### Verification
- [ ] File plays in VLC / QuickTime / Windows Media Player
- [ ] Audio is in sync with video
- [ ] Text overlays are readable
- [ ] No black frames at start or end
- [ ] File size under 100 MB
- [ ] All 5 segments present and in order
- [ ] Total runtime: 55–65 seconds

---

## 5. YouTube Upload Checklist

- [ ] Sign in to YouTube Studio (https://studio.youtube.com)
- [ ] Click "Create" → "Upload videos"
- [ ] Select file: `sage-demo-video.mp4`
- [ ] **Title:** `Sage — Your CRM that listens | Amazon Developer Hackathon 2026`
- [ ] **Description:** Copy from `docs/youtube-description.md`
- [ ] **Thumbnail:** Upload custom thumbnail (1280×720, see below)
- [ ] **Visibility:** Unlisted (change to Public after hackathon submission)
- [ ] **Tags:** `hackathon`, `alexa`, `mcp`, `sales`, `ai`, `amazon`, `nova`, `bedrock`, `crm`, `voice`, `alexaplus`
- [ ] **End screen:** Add GitHub repo link (last 10 seconds)
- [ ] **Subtitles:** Auto-generate, then review and fix technical terms
- [ ] Copy video URL for Hackster.io submission
- [ ] Add video URL to GitHub README
- [ ] Add video URL to `docs/submission.md`

### Thumbnail Design
- [ ] Dimensions: 1280×720 pixels
- [ ] Include: "Sage" logo/name
- [ ] Include: "Your CRM that listens" tagline
- [ ] Include: "Amazon Developer Hackathon 2026" badge
- [ ] Use brand colors: dark background (#0f172a), accent color for text
- [ ] Create in Canva (free) or Figma
- [ ] Save as: `thumbnail.png`

---

## Quick Reference

| Item | Value |
|------|-------|
| Length | 60 seconds |
| Resolution | 1920×1080 |
| Frame rate | 30 fps |
| Format | MP4 (H.264) |
| Audio | AAC 48 kHz |
| Video bitrate | 8000 Kbps |
| Audio bitrate | 160 kbps |
| File size | < 100 MB |
| YouTube visibility | Unlisted → Public |
| Thumbnail | 1280×720 |
| Takes | 5 (one per segment) |
