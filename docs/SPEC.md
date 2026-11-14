# Pythagoras: AI Oral Interviewer for Project-Based Assessment

> A real-time voice interviewer that probes students in depth about their own projects and gives the professor a ready-to-use assessment package to start the oral exam from.
>
> **Challenge direction:** Assessment

---

## 1. The Problem

**AI is being misused in student projects, and professors have too many students and too many courses to assess every project in depth.**

The problem is how professors **assess the projects students carry out**. They need to judge **how well each student actually knows the project they present**, now that AI is part of how projects get made.

- **A deliverable no longer proves understanding.** A polished report or working codebase can be largely AI-generated, and AI-text detectors perform close to chance.
- **In-depth assessment does not scale.** With 200 students at 15–20 minutes each, oral exams take 50–60 hours per session. Much of that time goes to basic questions ("define X") that don't separate students who understood from students who memorised.
- **The professor doesn't know where to start.** Faced with an AI-assisted project, the professor has no quick way to find which parts the student really owns and which they don't.

### Our answer
An **AI assistant that asks in-depth questions in real time and produces a report for the professor**, so the professor can see **how well each student actually knows their own project**.

---

## 2. Solution Overview

Pythagoras works in **three phases**:

```
 PHASE 1: PREPARE           PHASE 2: INTERVIEW            PHASE 3: PROFESSOR PACKAGE
 (asynchronous, offline)    (real time, 10 min, voice)    (asynchronous)

 Course content  ─┐                                       ┌─► 1. Student deliverable (as is)
 Syllabus        ─┼─► Interview plan ─► Live voice   ─────┼─► 2. Summary + brief critical analysis
 Deliverable     ─┘   (topics, questions,  interview      └─► 3. AI interview results
                       expected answers)   (time-limited,
                                           webcam on)
```

1. **Prepare (asynchronous).** The AI analyses the **course content**, the **syllabus** and the **student's deliverable** ahead of time. It prepares the **topics and questions** for the interview and a brief critical analysis of the project.
2. **Interview (real time, 10 minutes).** A voice interview with **limited time** and **webcam on**, so students cannot look up answers elsewhere. Questions adapt to the answers: vague answers get probed, solid answers lead to harder questions.
3. **Professor package (asynchronous).** The professor receives **three outputs** and uses them as the starting point for the human oral exam.

> **Pythagoras does not assign the grade.** It prepares the human oral exam. The professor stays in control of the final assessment.

---

## 3. State of the Art and Positioning

| Project | What it does | Known limitations |
|---|---|---|
| **NYU Stern** (Ipeirotis & Rizakos, 2026) | Final oral exam run by an ElevenLabs voice agent; grading by a "council" of 3 LLMs | **83%** of students found it more stressful. The agent sometimes **asked several questions at once**, with an "intense" voice. The validity of LLM grading has not been demonstrated. |
| **Socratic Mind** (Georgia Tech) | Socratic assessment, mostly text-based | Evidence is mostly students' self-reported perceptions |
| **Anthropic Interviewer** (Dec 2025) | Large-scale qualitative interviews in three stages: plan, interview, analysis | Built for research, not assessment |

### How Pythagoras is different
1. **It prepares the human oral exam instead of grading.** The AI runs a focused 10-minute screening and gives the professor evidence and suggested questions. The human oral becomes shorter and more targeted.
   - Under the **EU AI Act**, AI systems used to evaluate learning outcomes, and to monitor students during tests, are classified as **high-risk** (Annex III, point 3) and require human oversight. Keeping the human in charge of the grade is therefore also the right regulatory choice. Check the current timeline of the obligations.
2. **Questions are built on the student's own work** (their project), not generic course questions, and grounded in the syllabus learning objectives.
3. **Three separate outputs.** The professor sees the original work, an independent critical reading of it, and the evidence from the interview side by side.
4. **Designed against anxiety**, to avoid the problems seen at NYU: one question at a time, thinking pauses tolerated, "I don't know" accepted without penalty, and an unlimited practice mode.

---

## 4. Phase 1: Asynchronous Preparation

### Inputs
- **Course content:** slides, lecture notes, transcripts, reference material.
- **Syllabus:** learning objectives, expected competences, assessment criteria.
- **Student deliverable:** report (PDF), code repository, slides, dataset.

### What the AI does (with a powerful model, no latency constraints)
1. **Maps the deliverable to the syllabus.** Which learning objectives does the project cover, and how well?
2. **Extracts 4–6 key claims or design choices** worth verifying. For example: "chose a random forest over logistic regression", "used 5-fold cross-validation", "claims feature X is the main driver".
3. **Detects weak spots and red flags** in the deliverable: unjustified choices, errors (such as data leakage in the code), sections whose quality is inconsistent with the rest, claims that don't match the code.
4. **Builds the interview plan.** For each topic it prepares a ladder of questions by Bloom level, the **expected answers** used as evaluation criteria, and a time budget.
5. **Writes the summary and brief critical analysis** of the project (Output 2).

### Example interview plan (excerpt)
```json
{
  "student": "S-0421",
  "duration_s": 600,
  "topics": [
    {
      "id": "model_choice",
      "claim": "Random forest chosen over logistic regression (report, sec. 3.2)",
      "learning_objective": "LO3: select and justify ML models",
      "priority": "high",
      "time_budget_s": 150,
      "questions_by_bloom": {
        "2_understand": "Explain in your own words how a random forest works.",
        "4_analyze":    "Why did it outperform logistic regression on your data?",
        "5_evaluate":   "What are the limits of this choice? What would you change?"
      },
      "expected_points": ["non-linearity", "feature interactions", "interpretability trade-off"]
    },
    {
      "id": "validation",
      "claim": "5-fold cross-validation (report, sec. 4.1)",
      "red_flag": "Code applies StandardScaler before the train/test split (possible leakage)",
      "priority": "high",
      "time_budget_s": 150
    }
  ]
}
```

---

## 5. Phase 2: The Real-Time Interview (10 Minutes)

### 5.1 How modern AI interviewers manage to go in depth

> **A single prompt saying "run an in-depth interview" does not work.** The LLM tends to repeat patterns, ask several questions at once, lose the thread and settle for shallow answers. Systems that work rely on a few specific techniques.

#### a) Plan first, then interview
Both Anthropic Interviewer and the NYU system separate the phases. The plan is prepared offline in Phase 1, and the live interview follows the plan while adapting to the answers.

#### b) Structured state, not just chat history
The agent keeps a state object that is updated on every turn:
```json
{
  "topics": [
    {"id": "model_choice", "max_bloom_reached": 4, "failed_attempts": 0, "status": "deepen"},
    {"id": "validation",   "max_bloom_reached": 2, "failed_attempts": 2, "status": "closed_weak"}
  ],
  "time_left_s": 340,
  "inconsistencies": ["says k-fold was used; report and code show an 80/20 holdout"]
}
```
The system always knows **where it is** in the interview and doesn't lose track after 10 minutes of conversation.

#### c) Two agents: one talks, one thinks
This is the key pattern for **combining depth with low latency** (see also VoiceAgentRAG, arXiv 2603.02206, on dual-agent architectures):

```
                +-------------------------------+
 audio --> STT->|  TALKER (fast LLM)            |-> TTS --> audio
                |  - replies in < 1 s           |
                |  - executes the "next move"   |
                +---------------^---------------+
                                | next move + state
                +---------------+---------------+
                |  SUPERVISOR (strong LLM)      |   asynchronous, in background
                |  - evaluates the last answer  |
                |  - updates state / Bloom level|
                |  - picks the next move        |
                |  - detects inconsistencies    |
                +-------------------------------+
```
The talker does not reason deeply. It carries out the move the supervisor has already prepared ("ask for a counterexample on choice X") and phrases it naturally. The supervisor reasons calmly while the student is speaking, so the deep reasoning stays off the latency-critical path.

#### d) An explicit repertoire of probing moves
The supervisor picks from defined moves, inspired by qualitative interviewing practice (Geiecke & Jaravel: one point at a time, follow-ups that clarify every claim):

| Move | Example | When to use it |
|---|---|---|
| Clarification | "What exactly do you mean by 'works better'?" | Vague answer |
| Concrete example | "Give me a concrete case from your project." | Abstract or textbook answer |
| Justification | "Why this choice and not Y?" | Unjustified choice |
| Counterfactual | "What would happen if the data were imbalanced?" | Solid answer: move up a level |
| Objection | "A colleague says your result is overfitting. What do you reply?" | Testing robustness |
| Transfer | "How would you apply this idea to a different problem?" | High Bloom level |
| Deliverable check | "Your report says Z, but you just said W. How do they fit together?" | Inconsistency detected |
| Scaffold and exit | "Here's a hint: think about... OK, let's move on." | Two failed attempts |

#### e) Explicit progression rules (Bloom's taxonomy)
Bloom's taxonomy orders levels of understanding from shallow to deep: 1. Remember, 2. Understand, 3. Apply, 4. Analyze, 5. Evaluate, 6. Create.

- **Solid answer:** move up one Bloom level on the same topic.
- **Vague answer:** ask one clarification question, once.
- **Two failed attempts:** step down a level or give a hint, then **close the topic**. The AI does not keep pushing; the outcome itself is data for the report.
- **Time budget per topic**, so that every planned topic gets covered.

Reciting a definition (level 1) is easy even for a student who had ChatGPT write the project. A student who truly understands it holds up at levels 4–5, analysis and critical evaluation. The report shows **how far the student got on each topic**.

#### f) Turn-taking and thinking pauses
With classic silence detection (VAD), the AI interrupts students while they think, which is unacceptable in an exam.
- Use a **semantic end-of-turn detector**: Pipecat's *Smart Turn v3* (open source, BSD-2, 23 languages) or LiveKit's turn detector. These tell whether a sentence is finished or the student is just thinking ("so... uhm...").
- Use a long silence threshold of 2–3 seconds instead of 0.5.
- After a long pause the AI reassures instead of pressing: "Take all the time you need."

### 5.2 Integrity: limited time and webcam on
The interview is designed so that **looking up answers elsewhere is impractical**:
- **Limited time:** 10 minutes in total, with a per-topic budget and a natural conversational pace. There is no time to query another AI between questions.
- **Webcam on:** the session is recorded, and simple signals are flagged for the professor, such as the student looking away from the screen repeatedly, another person in view, or the browser tab losing focus.
- **Questions specific to the student's own project**, with quick follow-ups and counterfactuals that cannot be prepared in advance.
- **Flags are evidence, not verdicts.** Any integrity flag is shown in the report with a timestamp and video clip for the professor to review. The system never sanctions automatically.

> **Compliance note:** the EU AI Act **prohibits emotion recognition in educational settings** (Art. 5(1)(f)). The webcam must be used only for presence and attention signals, never to infer stress, emotions or "honesty". No biometric identification without an explicit legal basis.

---

## 6. Phase 3: The Professor Package (Three Outputs)

For each student the professor receives **three outputs**, to read side by side:

| # | Output | Purpose |
|---|---|---|
| **1** | **Student deliverable, as is** | The original, unmodified work. The source of truth. |
| **2** | **Summary and brief critical analysis of the project** | Understand the project in 2 minutes and know its strengths and weak spots before the oral |
| **3** | **AI interview results** | Evidence of how well the student actually knows their own project |

### Output 1: Student deliverable (as is)
The submitted files (report, code, slides), unmodified, with **anchors** linked from Outputs 2 and 3. For example, "sec. 3.2" or "train.py, line 41" open the exact passage.

### Output 2: Summary and brief critical analysis
```
PROJECT SUMMARY: "Customer Churn Prediction" (S-0421)

WHAT IT DOES (5 lines)
Predicts telecom customer churn from 18 features. Compares logistic
regression and random forest; RF reaches 0.87 AUC. Includes a feature
importance analysis and a short business recommendation.

COVERAGE OF SYLLABUS LEARNING OBJECTIVES
  LO1 Data preparation        covered, adequate
  LO2 Model selection         covered, good
  LO3 Validation              covered, with issues (see below)
  LO4 Interpretation          partially covered

STRENGTHS
  - Clear motivation for model comparison (sec. 3.2)
  - Well-structured code and reproducible notebook

WEAK SPOTS AND RED FLAGS
  - Possible data leakage: scaler fitted before the train/test split
    (train.py, line 41)
  - Report claims 5-fold CV, but the code uses an 80/20 holdout
  - Sec. 5 (business recommendation) is much more polished than the
    rest and is not supported by the analysis
```
This is a **critical reading of the work**, not a grade and not an "AI-generated" verdict. It tells the professor what to look at.

### Output 3: AI interview results
```
PYTHAGORAS INTERVIEW REPORT: S-0421, "Customer Churn Prediction"     10 min

SUMMARY (3 lines)
Solid command of model choice and feature engineering.
Weak understanding of validation: cannot explain the data leakage
in their own code.

DEPTH BY TOPIC                        Bloom level reached
  Model choice          [##########]  5 - Evaluate
  Feature engineering   [########--]  4 - Analyze
  Validation            [####------]  2 - Understand    (!)
  Interpretation        [######----]  3 - Apply

EVIDENCE (timestamped, click to play)
  [03:12] "I did the scaling before the split because it's easier"
          -> leakage not recognised, even after a hint
  [06:40] Justifies random forest vs logistic regression well, mentions
          the interpretability/performance trade-off unprompted

INCONSISTENCIES WITH THE DELIVERABLE
  - Report states "5-fold cross-validation"; student describes an
    80/20 holdout

INTEGRITY FLAGS (for review, not a verdict)
  - [07:55] Looked away from the screen for ~8 s before answering
    (video clip attached)

SUGGESTED QUESTIONS FOR THE ORAL EXAM (start here)
  1. "Let's walk through your pipeline: where do you fit the scaler?"
  2. "Who wrote section 5? Walk me through how you reached that
     recommendation."

REPORT RELIABILITY
  3 models agree on 3 of 4 topics. Disagreement on "Interpretation":
  needs human check.
```

### Design choices for the package
- **No grade**, only evidence. Every statement is **anchored to a quote and a timestamp**, or to a passage in the deliverable, so the professor can verify it.
- **Multi-LLM council** (as at NYU) to produce the report. Disagreements are flagged, not hidden.
- **Suggested questions** for the human oral are the hand-off from the AI to the professor.
- **The professor sees each output separately**: the work, an independent reading of the work, and how the student defended it.

---

## 7. Technology Stack

### Two possible architectures
| | **Cascade** (STT -> LLM -> TTS) | **Speech-to-speech** (OpenAI Realtime, Gemini Live) |
|---|---|---|
| Latency | ~600–1000 ms | ~300–600 ms |
| Control over reasoning and state | Full | Limited |
| Reliable transcript for the report | Native | Separate |
| Talker/supervisor pattern | Natural | More complex |
| Language quality | Pick the best STT and TTS | Good |

**Recommendation: cascade.** For an exam, traceability and control matter more than 300 ms less latency.

### Three concrete options
| Option | Components | Pros | Cons |
|---|---|---|---|
| **A. Speed** (used by NYU) | ElevenLabs Agents with workflows and dynamic variables, plus an LLM of your choice | Working demo in a few hours | Little control over the supervisor; closed platform |
| **B. Control (recommended)** | **Pipecat** (open source) + Smart Turn v3 + STT (Deepgram, Gladia or Whisper) + LLM + TTS (ElevenLabs or Cartesia) | Dual-agent pattern, custom state, all in Python | More integration work |
| **C. Virtual room + webcam** | **LiveKit Agents** (Apache-2.0) | WebRTC, video stream (needed for webcam on), rooms | More infrastructure |

Since the interview requires **webcam on**, a good combination is **LiveKit** for the audio/video room and recording, with **Pipecat-style** pipeline logic, or LiveKit Agents alone.

**LLMs:**
- **Phase 1 and Phase 3** (preparation, critical analysis, report): a strong model with no latency constraints, such as Claude Opus 5.5 or Sonnet 5.5, with a multi-model council for the report.
- **Phase 2 talker:** a fast model, such as Claude Haiku 5.5.
- **Phase 2 supervisor:** a strong model running asynchronously, such as Claude Sonnet 5.5.

### Open-source projects to study
- **Pipecat** and its examples (pipelines, interruptions, Smart Turn).
- **LiveKit Agents**.
- **Geiecke & Jaravel, "Conversations at Scale"**: an open-source platform for AI-led interviews, with probing prompts rated by experts. The closest reference for the "go in depth" part.
- The **prompts published by NYU** for their voice agent and grading council.

---

## 8. Risks, Ethics and Compliance

| Risk | Mitigation |
|---|---|
| Anxiety (83% at NYU) | Unlimited practice mode, calm voice, one question at a time, no grade from the AI |
| Transcription errors (accents, technical terms, hesitations) | Course glossary passed to STT; professor can replay the audio |
| LLM "inventing" inconsistencies or red flags | Every flag must quote the deliverable passage and the transcript moment |
| Student reading answers from another AI | Time limit, webcam on, questions specific to their own project, fast counterfactuals; the human oral remains the final check |
| Webcam false positives (looking away to think) | Flags are review prompts with video clips, never automatic sanctions |
| Emotion recognition | **Prohibited** in education under the EU AI Act: use only presence and attention signals |
| Fairness (learning disabilities, non-native speakers, connectivity) | Configurable extended time, option to answer in writing, reschedule on technical failure |
| GDPR and AI Act (high-risk system) | Human oversight, informed consent, minimal data retention, no automated decisions, transparency to students |

---

## 9. MVP Plan

**Scope:** one course (such as Machine Learning) and one deliverable type (project report PDF plus code).

| Step | Work |
|---|---|
| 1 | **Ingestion:** upload syllabus, course materials and the deliverable |
| 2 | **Planner (Phase 1):** deliverable + syllabus -> interview plan JSON (topics, claims, red flags, Bloom ladders, expected answers) and Output 2 (summary and critical analysis) |
| 3 | **Voice pipeline (Phase 2):** LiveKit or Pipecat with STT, talker, TTS and Smart Turn; webcam recording; 10-minute timer |
| 4 | **Asynchronous supervisor:** evaluates each answer, updates state, picks the next move from the repertoire |
| 5 | **Professor package (Phase 3):** dashboard with the 3 outputs side by side, with timestamps, quotes and suggested questions |
| 6 | **Evaluation:** 5–10 interviews with "prepared" and "unprepared" peers (for example, defending a project that isn't theirs). Check that the report tells them apart. |

### Demo in three acts
1. **A prepared student:** the AI climbs to Bloom level 5.
2. **A student who "had AI do the project":** holds up on definitions, collapses on the counterfactual and on the leakage in their own code.
3. **The professor opens the package:** in 30 seconds they see the work, its weak spots and how the student defended it, and know exactly where to start the oral.

> **Pitch metric:** "The report agrees with the professor's judgement on X of Y topics, and the human oral drops from 20 to 8 minutes per student."

---

## 10. Sources

- [Ipeirotis & Rizakos: Scalable and Personalized Oral Assessments Using Voice AI (arXiv 2603.18221)](https://arxiv.org/html/2603.18221)
- [CACM version](https://cacm.acm.org/practice/scalable-and-personalized-oral-assessments-using-voice-ai/)
- [The Decoder: costs and published prompts](https://the-decoder.com/nyu-professor-fights-ai-cheating-with-ai-powered-oral-exams-that-cost-42-cents-per-student/)
- [Washington Square News: NYU student experience](https://nyunews.com/news/2026/01/28/stern-professors-ai-exams/)
- [Fighting Fire with Fire (blog)](https://allarddewinter.net/blog/fighting-fire-with-fire-scalable-oral-exams-with-voice-ai/)
- [Critique: When AI Grades Oral Exams](https://drlaurentflores.substack.com/p/when-ai-grades-oral-exams-pedagogical)
- [Socratic Mind: Georgia Tech](https://cc.gatech.edu/news/ai-oral-assessment-tool-uses-socratic-method-test-students-knowledge) and [paper (arXiv 2509.16262)](https://arxiv.org/pdf/2509.16262v2)
- [Fortune: the return of oral exams](https://fortune.com/2026/04/23/the-gen-z-stare-meets-the-mysterious-perfect-homework-assignment-in-the-age-of-chatgpt-enter-the-oral-exam/)
- [Geiecke & Jaravel: Conversations at Scale (SSRN)](https://papers.ssrn.com/abstract=4974382) and [NBER slides](https://conference.nber.org/conf_papers/f221279/f221279.slides.pdf)
- [ACL 2026 demo: multi-agent interview pipeline](https://aclanthology.org/2026.acl-demo.12.pdf)
- [About Anthropic Interviewer](https://www.anthropic.com/about-anthropic-interviewer)
- [VoiceAgentRAG: dual-agent architectures (arXiv 2603.02206)](https://arxiv.org/pdf/2603.02206)
- [Pipecat vs LiveKit Agents (2026)](https://www.forasoft.com/blog/article/pipecat-vs-livekit-agents)
- [Best Open Source Voice AI Agent Frameworks 2026](https://micdrop.dev/blog/open-source-voice-agent-frameworks)
- [Semantic End-of-Turn Detection (arXiv 2510.04016)](https://arxiv.org/pdf/2510.04016)
- [Voice stack latency benchmark (DEV)](https://dev.to/kenimo49/i-benchmarked-5-voice-ai-stacks-only-2-stayed-under-300ms-2bka)
- [Inworld: speech-to-speech model comparison](https://inworld.ai/resources/best-speech-to-speech-model)
- [Keystroke Dynamics vs LLM-assisted dishonesty (arXiv 2511.12468)](https://arxiv.org/html/2511.12468v2): context on why AI-text detection is unreliable

*Note: latency figures come from single-author or vendor benchmarks; measure them yourself for your target language. Several cited studies are preprints that have not yet been peer reviewed. Verify the current EU AI Act timelines before relying on them.*
