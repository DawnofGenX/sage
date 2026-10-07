# Sage Demo Video Recording Plan

**Target length:** 60 seconds  
**Resolution:** 1920×1080 (1080p)  
**Frame rate:** 30 fps  
**Format:** MP4 (H.264)  
**Audio:** 48 kHz, 16-bit stereo

---

## 1. Screen Recording Setup

### OBS Studio (Free, Cross-Platform)

1. **Install OBS Studio** — https://obsproject.com/
2. **Scene Configuration:**
   - Scene 1: "Simulator" — Display Capture of browser at 1920×1080
   - Scene 2: "Code" — Display Capture of VS Code / terminal
   - Scene 3: "Architecture" — Display Capture of architecture.md rendered
3. **Browser Setup:**
   - Open web simulator at `http://localhost:3000`
   - Set browser zoom to 100%
   - Use a clean Chrome profile (no bookmarks bar, no extensions)
   - Window size: 1920×1080 exactly
4. **Audio:**
   - Microphone: USB condenser mic (Blue Yeti, Audio-Technica AT2020, or equivalent)
   - Record a test clip — check levels peak around -12 dB to -6 dB
   - Disable desktop audio (we'll add background music in post)
5. **Recording Settings:**
   - Output → Recording → Type: Standard
   - Recording Format: mp4
   - Video Bitrate: 8000 Kbps
   - Audio Bitrate: 160 kbps
   - Encoder: x264 (or hardware NVENC if available)

### Alternative: QuickTime (Mac) / Xbox Game Bar (Windows)

- QuickTime: File → New Screen Recording → select region → record
- Xbox Game Bar: Win+G → Capture → Start Recording

---

## 2. Recording Checklist

Record in this order. Each segment is a separate take — you can stop and restart between segments.

### Pre-Recording
- [ ] Close all unnecessary applications
- [ ] Disable notifications (Focus Mode / Do Not Disturb)
- [ ] Clear browser cache and cookies
- [ ] Open web simulator and verify it loads correctly
- [ ] Test microphone levels
- [ ] Record 5-second test clip and verify audio/video sync

### Segment 1: The Problem (0:00–0:10)
- [ ] Show split screen: salesperson on call (stock photo or illustration) vs. typing in CRM
- [ ] On-screen text overlay: "2+ hours/day on data entry"
- [ ] Voiceover: "Salespeople spend over two hours a day on CRM data entry. Deals fall through the cracks. Follow-ups get forgotten."

### Segment 2: Passive Listening (0:10–0:25)
- [ ] Show Echo device illustration or stock photo
- [ ] Switch to web simulator — VoiceInput component
- [ ] Click "Start Listening" or type a sample transcript
- [ ] Show live transcript appearing in TranscriptView
- [ ] On-screen text: "Call in progress..."
- [ ] Voiceover: "Sage listens passively. No wake words, no commands. Just have the conversation."

### Segment 3: Auto-Extraction (0:25–0:40)
- [ ] Show ExtractionPipeline component
- [ ] Trigger extraction (click "Extract" or auto-trigger after transcript)
- [ ] Show all 4 stages completing: Entity Extraction → Intent Classification → Record Generation → Schema Validation
- [ ] On-screen text: "Extracting insights..."
- [ ] Voiceover: "After the call, Sage extracts everything using Amazon Nova: contacts, deals, follow-ups, sentiment, buying signals."

### Segment 4: Proactive Insight (0:40–0:50)
- [ ] Show ProactiveInsights component
- [ ] Display insight cards with urgency coding (overdue/stuck/info)
- [ ] Highlight the Acme insight: "You haven't followed up with Acme in 20 days. Their Q4 budget deadline is Friday."
- [ ] Voiceover: "And Sage doesn't wait for you to ask. It proactively tells you what you're forgetting."

### Segment 5: CRM Sync + Close (0:50–1:00)
- [ ] Show PipelineBoard component with Kanban columns
- [ ] Click "Sync to CRM" button
- [ ] Show sync animation completing
- [ ] On-screen text: "Synced to Salesforce ✓"
- [ ] Voiceover: "Everything synced to your CRM automatically. Sage. Your CRM that listens."
- [ ] End card: GitHub repo URL + "Built for Amazon Developer Hackathon 2026"

### Post-Recording
- [ ] Review all takes — pick the best one for each segment
- [ ] Note timestamps of best takes for editing

---

## 3. Voiceover Script

Record in a quiet room. Speak at a natural, conversational pace. Smile while recording — it changes your tone.

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
- Keep energy up but not salesy — conversational, confident

---

## 4. Editing Workflow

### DaVinci Resolve (Free)

1. **Import** all takes into Media Pool
2. **Create Timeline** — 1920×1080, 30 fps
3. **Assemble** best takes in order on Video Track 1
4. **Add B-roll** on Video Track 2:
   - Stock photos: salesperson on call, Echo device, office setting
   - Use Pexels or Unsplash (free, no attribution required)
5. **Add Text Overlays** (Fusion → Text+):
   - "2+ hours/day on data entry" — Segment 1
   - "Call in progress..." — Segment 2
   - "Extracting insights..." — Segment 3
   - "Synced to Salesforce ✓" — Segment 5
   - End card with repo URL
6. **Add Voiceover** on Audio Track 1
7. **Add Background Music** on Audio Track 2:
   - Use YouTube Audio Library (free, no copyright issues)
   - Choose something upbeat but not distracting
   - Duck music to -20 dB under voiceover
8. **Color Correction** (optional):
   - Slight brightness/contrast boost for screen recordings
   - Ensure text is readable
9. **Transitions:**
   - Simple cross-dissolves between segments (0.5 seconds)
   - No fancy transitions — keep it clean

### Alternative: iMovie (Mac) / Clipchamp (Windows)

- Same workflow: import → assemble → add text → add voiceover → add music → export

---

## 5. Export Settings

### DaVinci Resolve Export

1. File → Export → Render
2. Format: MP4
3. Codec: H.264
4. Resolution: 1920×1080
5. Frame rate: 30 fps
6. Quality: Automatic (or restrict to 8000 Kbps)
7. Audio: AAC, 48 kHz, 160 kbps
8. Filename: `sage-demo-video.mp4`

### Verification

- [ ] File plays in VLC / QuickTime / Windows Media Player
- [ ] Audio is in sync with video
- [ ] Text overlays are readable
- [ ] No black frames at start or end
- [ ] File size under 100 MB (for YouTube upload)

---

## 6. Upload Checklist

### YouTube Upload

1. **Sign in** to YouTube Studio (https://studio.youtube.com)
2. **Create** → **Upload videos**
3. **Select file:** `sage-demo-video.mp4`
4. **Title:** `Sage — Your CRM that listens | Amazon Developer Hackathon 2026`
5. **Description:** Copy from `docs/youtube-description.md`
6. **Thumbnail:** Upload custom thumbnail (see below)
7. **Visibility:** Unlisted (or Public if ready for the world)
8. **Tags:** `hackathon`, `alexa`, `mcp`, `sales`, `ai`, `amazon`, `nova`, `bedrock`, `crm`, `voice`
9. **End screen:** Add GitHub repo link (last 10 seconds)
10. **Subtitles:** Auto-generate, then review and fix any errors

### Thumbnail

- Create in Canva (free) or Figma
- 1280×720 pixels
- Include: Sage logo/name, "Your CRM that listens" tagline, hackathon badge
- Use brand colors (dark background, accent color for text)

### Post-Upload

- [ ] Verify video plays correctly on YouTube
- [ ] Check auto-generated captions for accuracy
- [ ] Copy video URL for Hackster.io submission
- [ ] Add video URL to GitHub README
- [ ] Add video URL to submission.md

---

## Quick Reference

| Item | Value |
|------|-------|
| Length | 60 seconds |
| Resolution | 1920×1080 |
| Frame rate | 30 fps |
| Format | MP4 (H.264) |
| Audio | AAC 48 kHz |
| File size | < 100 MB |
| YouTube visibility | Unlisted |
| Thumbnail | 1280×720 |
