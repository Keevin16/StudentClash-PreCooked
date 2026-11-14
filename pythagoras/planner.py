"""Phase 1: deliverable + assignment -> interview plan and critical analysis (reasoner model)."""
import base64
import json
from pathlib import Path
from typing import List

from . import config, llm
from .models import InterviewPlan

CODE_EXT = {".py", ".r", ".rmd", ".qmd", ".sql", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".m", ".jl"}
TEXT_EXT = CODE_EXT | {".md", ".txt", ".py", ".r", ".rmd", ".qmd", ".sql", ".tex", ".csv", ".json", ".yaml", ".yml",
            ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".m", ".jl", ".html", ".css"}
MAX_TEXT_CHARS = 150_000  # per file; larger text files are cut and marked as such

SYSTEM = """You prepare a short one-on-one oral screening (about {minutes} minutes) between an AI interviewer and
a TEAM of students about the team's OWN project deliverable (the member who worked on a part answers about it).
The goal is to find out how deeply the team understands what it submitted - not to grade it.

Produce:
1. topics: exactly {topics} topics worth probing, ordered by priority. The title is a neutral name of the area ("Weight
   initialisation", never "Initialisation bug"): the team sees it on screen. Each topic is anchored to a precise place in the
   deliverable (page/section or file:line), states what the deliverable claims or decides there, and has a
   time budget (the budgets sum to about {seconds} seconds). Prefer design decisions, results, trade-offs and
   suspicious spots (inconsistencies, unjustified choices, things that look copied or generated) over
   definitions. For each topic write one question per Bloom level 2 (Understand), 3 (Apply), 4 (Analyze) and
   5 (Evaluate), each answerable orally in under a minute, with the points a good answer must mention.
   Questions must be about THIS project, never generic textbook questions. Never give away a flaw you
   found: ask the team to explain or justify what they did there, so the flaw surfaces (or not) from their
   own answer; only the level 4-5 questions may confront them with it (level 2, good: "Walk me through how
   you set the initial weights." Bad: "Why is starting from zero weights a problem?"). They will be spoken aloud: one
   short question each (under 35 words), no formulas, symbols or lists, nothing that needs to be seen.
2. analysis: a brief critical analysis for the professor: what the project does, strengths and weak spots
   (each anchored), and coverage of the learning objectives if any are given.
Write everything in {language}; topic ids stay short lowercase ASCII slugs."""


def _blocks(folder: Path, label: str) -> List[dict]:
    blocks: List[dict] = []
    for p in sorted(folder.iterdir()) if folder.exists() else []:
        ext = p.suffix.lower()
        if ext == ".pdf":
            blocks.append({"type": "document", "title": f"{label}: {p.name}",
                           "source": {"type": "base64", "media_type": "application/pdf",
                                      "data": base64.standard_b64encode(p.read_bytes()).decode()}})
        elif ext == ".ipynb":
            nb = json.loads(p.read_text(errors="replace"))
            cells = ["".join(c.get("source", [])) for c in nb.get("cells", [])]
            blocks.append(_text(f"{label}: {p.name} (notebook cells)", "\n\n# ---\n".join(cells)))
        elif ext in CODE_EXT:  # numbered, so topics can be anchored as file:line
            lines = p.read_text(errors="replace").splitlines()
            blocks.append(_text(f"{label}: {p.name} (line-numbered)",
                                "\n".join(f"{i:4}| {ln}" for i, ln in enumerate(lines, 1))))
        elif ext in TEXT_EXT:
            blocks.append(_text(f"{label}: {p.name}", p.read_text(errors="replace")))
        else:
            blocks.append({"type": "text", "text": f"[{label}: {p.name} - format not readable, ignored]"})
    return blocks


def _text(title: str, body: str) -> dict:
    if len(body) > MAX_TEXT_CHARS:
        body = body[:MAX_TEXT_CHARS] + "\n[... file truncated ...]"
    return {"type": "text", "text": f"===== {title} =====\n{body}"}


def make_plan(deliverable: Path, materials: Path, assignment: dict, duration_s: int) -> InterviewPlan:
    brief = (f"Assignment: {assignment['title']}\nCourse: {assignment['course'] or '-'}\n"
             f"Description: {assignment['description'] or '-'}\n"
             f"Learning objectives:\n{assignment['objectives'] or '- (none given)'}")
    content = [{"type": "text", "text": brief}, *_blocks(materials, "Course material"),
               *_blocks(deliverable, "Student deliverable"),
               {"type": "text", "text": "Prepare the interview plan for this deliverable."}]
    plan = llm.parse(InterviewPlan, SYSTEM.format(minutes=duration_s // 60, seconds=duration_s, language=config.LANGUAGE_NAME, topics=config.TOPICS), content,
                     effort="high")
    plan.duration_s = duration_s
    plan.topics = plan.topics[:config.TOPICS]  # the model may add one more
    for t in plan.topics:
        t.questions.sort(key=lambda q: q.level)
    return plan
