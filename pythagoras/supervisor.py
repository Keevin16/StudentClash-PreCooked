"""Judges one answer against the plan (reasoner model). The rules that act on the verdict live in engine.py."""
import json

from . import config, llm
from .models import BLOOM, Evaluation, InterviewPlan, Move, Topic

SYSTEM = """You judge ONE spoken answer in a short oral screening where a team of students explains its OWN project
(one member answers at a time).
The answer is a speech transcript: ignore filler words, small grammar slips and transcription errors.
Verdicts:
- solid: a correct, specific answer at the asked Bloom level that shows the team understands its own work.
  It does not need to cover every expected point; a decent correct answer is solid.
- partial: on track but vague, generic, or missing the key point for this level.
- weak: mostly wrong, or only restates the question / the deliverable without understanding.
- dont_know: they say they don't know or don't remember.
- off_topic: the answer is about something else.
A pause, a restart or a sentence cut short is normal in speech: judge the substance.
Judge only what was said, never reward length. The note is one neutral sentence for the professor, in {language}."""


def evaluate(plan: InterviewPlan, topic: Topic, move: Move, question: str, answer: str) -> Evaluation:
    if not answer.strip():
        return Evaluation(verdict="dont_know", covered_points=[], missing_points=[], note="(no answer)")
    planned = next((q for q in topic.questions if q.level == move.level), None)
    payload = {
        "topic": topic.title, "deliverable_claim": topic.claim, "anchor": topic.anchor,
        "bloom_level": f"{move.level} ({BLOOM.get(move.level)})",
        "question_asked": question,
        "expected_points": planned.expected_points if planned else [],
        "student_answer": answer,
    }
    return llm.parse(Evaluation, SYSTEM.format(language=config.LANGUAGE_NAME), json.dumps(payload, indent=1, ensure_ascii=False),
                     max_tokens=4000, fast=True)  # live: the student is waiting
