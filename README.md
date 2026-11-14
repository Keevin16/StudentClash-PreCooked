# Pythagoras

AI oral assessment for project-based courses. A **team** uploads its deliverable, receives an invite link and has a ~10-minute **spoken conversation** with Pythagoras about its own project (whoever worked on a part answers it). Pythagoras covers 3 topics and climbs Bloom's levels on each (Understand → Apply → Analyze → Evaluate) and hands the professor a report to start the oral exam from. **Pythagoras never assigns the grade.**

- What this version is and why (v0.3 platform + v0.2 voice): [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Pages and API contract: [`docs/API.md`](docs/API.md) · original spec: [`docs/SPEC.md`](docs/SPEC.md)
- **Guida di avvio (IT):** [`docs/GUIDA_AVVIO.md`](docs/GUIDA_AVVIO.md)

## Run

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[voice,dev]"   # Apple Silicon: natural local voice (needs `brew install espeak-ng`)
# pip install -e ".[dev]"       # any other machine: the browser's voice is used instead
cp .env.example .env            # set ONE key: OPENROUTER_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY (or PYTHAGORAS_FAKE_LLM=1 offline)
python -m pythagoras check         # one real call per model
python -m pythagoras serve         # first start downloads the voice models (~2.5 GB) into .cache/
```

- Professor: <http://localhost:8000/prof> (open by default; set `PYTHAGORAS_PROFESSOR_PASSWORD` to require a login): create an assignment.
- Quickest demo: on the student page click **Use the Pirelli case**: the interview opens with nothing to fill in (the first click prepares the plan in ~2 min, later clicks reuse it). The professor pages also show a finished **Team_1** report (topics, levels, quotes, questions for the oral exam). Without `cases/pirelli/` (not in the repo) both use the synthetic neural-network case (`cases/ffnn`, report in `cases/ffnn/team1.json`).
- Team: <http://localhost:8000/>: team name, contact email and files, then open the invite link (shown on screen when SMTP is not configured).
- `python scripts/smoke.py` runs a whole spoken interview with a synthetic student and prints the latency of each stage.

## The conversation

With the `voice` extra everything audio runs on the Mac: the page streams the microphone to the server, **Silero VAD + Smart Turn v3** decide when the answer is over (a finished sentence after 1 s of pause; an "uhm…" gets up to 2.5 s), **Whisper** transcribes, **Kokoro** speaks. The team just talks: nothing to press. While the answer is judged, Pythagoras says a short "Okay." at once and the likely follow-up is already being phrased, so the next question starts about 2–4 s after the team stops (measured on an M1 Pro with Claude Haiku via OpenRouter and with Gemini Flash Lite).

The team's webcam is on during the interview, shown with a **REC** badge and timer; the badge is only visual, **nothing is recorded or sent**. Leaving the tab or switching the camera off is noted for the professor as a review prompt.

LLM: on OpenRouter the defaults are Claude Sonnet 5.5 (plan, report) and Haiku 5.5 (judge, talker); a whole Pirelli interview including a new plan cost about $0.03.

Without the extra (or with `PYTHAGORAS_VOICE=browser`) the same page uses the browser's speech APIs (Chrome/Edge) and a "I'm done" button; Firefox falls back to typing.

## Layout

```
pythagoras/
  app.py          FastAPI: /api + static pages
  planner.py      Phase 1: deliverable (+ assignment, course material) -> plan + critical analysis   [reasoner]
  engine.py       Phase 2: interview rules (Bloom climb, probe, scaffold, budgets, wrap-up), speculative phrasing
  supervisor.py   judges each answer                                                             [reasoner, fast]
  talker.py       phrases what Pythagoras says                                                      [talker]
  report.py       Phase 3: report for the professor, quotes checked against the transcript        [reasoner]
  voice.py        local voice API: TTS stream + microphone WebSocket
  audio.py        VAD, end of turn, Whisper, Kokoro
  llm.py          the only LLM client (Gemini or Claude); fake.py = offline stub (PYTHAGORAS_FAKE_LLM=1)
  db.py           SQLite + files under data/
  mailer.py       invite email (SMTP) or data/outbox/
  static/         HTML/CSS/JS frontend, no build step: room.css = student pages (green template), app.css = professor
                  pages, voice-local.js + pcm-worklet.js = microphone transport
scripts/smoke.py  end-to-end spoken interview against a running server
tests/            offline (python -m pytest)
cases/ffnn/       synthetic test case: assignment, course notes, deliverable, answer key
```
