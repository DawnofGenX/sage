# Sage — Final Submission Checklist

**Use this checklist before submitting to Hackster.io and Amazon Developer Hackathon 2026.**

---

## 1. Code Complete & Tested

- [ ] All 23 MCP tools implemented and working
- [ ] All 298 tests passing (`pytest` in `mcp-server/`)
- [ ] Web simulator builds without errors (`npm run build`)
- [ ] Web simulator runs without console errors
- [ ] Docker Compose setup works (`docker compose up`)
- [ ] No TODO comments or placeholder code remaining
- [ ] No debug `print()` statements left in production code
- [ ] `.env` file not committed to git (use `.env.example`)
- [ ] `requirements.txt` and `package.json` are up to date
- [ ] Code formatted (Black for Python, Prettier for TypeScript)
- [ ] No linting errors

## 2. Documentation Complete

- [ ] `README.md` — project overview, features, quick start, MCP tools table
- [ ] `docs/architecture.md` — system architecture, data flow, component descriptions
- [ ] `docs/demo-script.md` — 60-second demo script with timestamps
- [ ] `docs/video-recording-checklist.md` — OBS setup, recording steps, export settings
- [ ] `docs/deployment.md` — deployment instructions (local, Docker, cloud)
- [ ] `docs/submission.md` — Hackster.io submission content
- [ ] `docs/submission-checklist.md` — Hackster.io form fields
- [ ] `docs/submission-final-checklist.md` — this checklist
- [ ] `docs/youtube-description.md` — YouTube title, description, tags
- [ ] `docs/screenshot-checklist.md` — screenshot capture checklist
- [ ] `docs/friction-log.md` — development challenges and learnings
- [ ] `docs/test-report.md` — test results and known issues
- [ ] `CONTRIBUTING.md` — contribution guidelines
- [ ] `LICENSE` — MIT license file
- [ ] All internal links in docs are valid (no 404s)

## 3. Demo Video

- [ ] Video recorded (see `docs/video-recording-checklist.md`)
- [ ] All 5 segments recorded:
  - [ ] Segment 1: The Problem (0:00–0:10)
  - [ ] Segment 2: Passive Listening (0:10–0:25)
  - [ ] Segment 3: Auto-Extraction (0:25–0:40)
  - [ ] Segment 4: Proactive Insight (0:40–0:50)
  - [ ] Segment 5: CRM Sync + Close (0:50–1:00)
- [ ] Video edited with voiceover, text overlays, and background music
- [ ] Video exported at 1080p, 30fps, MP4 (H.264)
- [ ] Video uploaded to YouTube (unlisted or public)
- [ ] YouTube title set: "Sage — Your CRM that listens | Amazon Developer Hackathon 2026"
- [ ] YouTube description added (from `docs/youtube-description.md`)
- [ ] YouTube tags added
- [ ] Custom thumbnail uploaded (1280×720)
- [ ] Auto-captions reviewed and corrected
- [ ] Video URL copied for Hackster.io submission
- [ ] Video URL added to GitHub README
- [ ] Video URL added to `docs/submission.md`

## 4. Screenshots Captured

- [ ] Screenshot 1: Main dashboard with hero section
- [ ] Screenshot 2: Auto-demo mode running
- [ ] Screenshot 3: Extraction pipeline in action
- [ ] Screenshot 4: Proactive insights with urgency cards
- [ ] Screenshot 5: Pipeline board (Kanban)
- [ ] Screenshot 6: Alexa+ view (Echo Show simulation)
- [ ] Screenshot 7: Call simulator with live transcript
- [ ] Screenshot 8: Forecast chart
- [ ] Screenshot 9: Activity feed
- [ ] Screenshot 10: Architecture diagram
- [ ] All screenshots saved to `screenshots/` directory
- [ ] All screenshots are 1920×1080
- [ ] No sensitive information visible
- [ ] All screenshots added to git and pushed to GitHub

## 5. GitHub Repository

- [ ] Repository is **public**
- [ ] Repository name is clear and descriptive (`sage`)
- [ ] `README.md` renders correctly on GitHub
- [ ] All files committed and pushed
- [ ] `.gitignore` excludes `node_modules/`, `__pycache__/`, `.env`, `dist/`, `*.db`
- [ ] No sensitive files committed (`.env`, credentials, etc.)
- [ ] License file present (MIT)
- [ ] Repository description set
- [ ] Topics/tags added: `mcp`, `alexa`, `sales`, `ai`, `amazon`, `hackathon`, `nova`, `bedrock`, `crm`
- [ ] Git commit history is clean (no "fix typo" commits)

## 6. Live Demo Deployed

- [ ] Web simulator deployed to Vercel / Netlify / Railway
- [ ] MCP server deployed (or accessible via public URL)
- [ ] Demo URL is accessible and loads correctly
- [ ] Demo URL works on mobile (responsive design)
- [ ] No CORS issues between frontend and backend
- [ ] Environment variables configured in deployment
- [ ] Demo URL added to README.md
- [ ] Demo URL added to `docs/submission.md`
- [ ] Demo URL added to YouTube description

## 7. Hackster.io Submission

- [ ] Project name: "Sage — The Alexa+ Sales Intelligence Layer"
- [ ] Elevator pitch: filled (under 200 chars)
- [ ] About the project: filled (copy from `docs/submission.md`)
- [ ] Built with tags: Python, TypeScript, React, MCP, Streamable HTTP, Amazon Nova, AWS Bedrock, Docker, MIT License
- [ ] Try it out links: GitHub repo, live demo, demo video
- [ ] Image gallery: all 10 screenshots uploaded
- [ ] Video demo: YouTube link added
- [ ] Project published (not draft)

## 8. All Links Verified

- [ ] GitHub repo URL works
- [ ] Live demo URL works
- [ ] YouTube video URL works
- [ ] Hackathon page URL works
- [ ] All links in README.md are valid
- [ ] All links in `docs/submission.md` are valid
- [ ] All links in YouTube description are valid
- [ ] All links in Hackster.io submission are valid

## 9. Final Polish

- [ ] Code formatted (Black for Python, Prettier for TypeScript)
- [ ] No linting errors
- [ ] Git commit history is clean
- [ ] Final git push completed
- [ ] All team members credited (if applicable)
- [ ] Thank-you note prepared for judges (optional)

---

## Submission Day Timeline

| Time | Task |
|------|------|
| T-2 hours | Final code review and test run (`pytest` + `npm run build`) |
| T-1.5 hours | Verify all links work (GitHub, demo, YouTube, hackathon) |
| T-1 hour | Record final demo video (if needed) |
| T-45 min | Upload video to YouTube |
| T-30 min | Capture final screenshots |
| T-15 min | Fill out Hackster.io form |
| T-5 min | Final review of all submission fields |
| T-0 | **Submit!** |

---

## Emergency Contacts

- Hackathon support: [hackathon support email/Discord]
- Hackster.io support: https://support.hackster.io/
- YouTube support: https://support.google.com/youtube/

---

**Good luck! 🚀**
