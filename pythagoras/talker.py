"""What Pythagoras says out loud (talker model): one short spoken line per move."""
import re
from typing import Optional

from . import config, llm
from .models import BLOOM, InterviewPlan, Move, Topic

SYSTEM = """You are Pythagoras, a calm, friendly university examiner in a short one-on-one spoken conversation with
a team of students about the team's own project; whoever worked on a part answers, so address the team
("you" plural), never one person by name. Speak {language}, informally and warmly, the way a person talks.
Your words are read aloud by text-to-speech, so:
- plain spoken language only: no markdown, lists, emoji, parentheses, symbols or formulas; write numbers and
  abbreviations the way they are said
- shape: first ONE bridging sentence of at most 8 words, ending with a full stop, that links to what the
  student just said or names the new topic ("So you went with a sigmoid." / "Let's move to your evaluation.");
  then ONE question in ONE sentence (unless told to ask nothing). About 35 words in total, never more than 50
- the bridge is neutral, never an opinion: no praise ("good", "great", "solid", "clear", "interesting"), no grading, no
  correction, no hint of the expected answer; do not open with a bare "Okay" or "Thanks" (an acknowledgement
  was just spoken)
- the question is about their project specifically and keeps the content of the planned question
- point to places in their work the way people talk ("in your training loop", "in section three"): never read
  out file names with extensions or line numbers
- the question is short and asks ONE thing: no "and" joining two questions, no "for example" lists
Reply with only the words to say, at most two sentences."""


def phrase(plan: InterviewPlan, topic: Optional[Topic], move: Move, last_answer: str = "") -> str:
    lines = [f"What to do now: {move.intent}"]
    if topic:
        planned = next((q for q in topic.questions if q.level == move.level), None) \
            or min(topic.questions, key=lambda q: abs(q.level - move.level))
        lines += [f"Topic: {topic.title} (in the deliverable: {topic.anchor})",
                  f"What the deliverable says: {topic.claim}",
                  f"Bloom level: {move.level} ({BLOOM.get(move.level)})",
                  f"Planned question: {planned.question}"]
        if move.kind in ("probe", "scaffold"):
            lines.append("Points a good answer would cover (do NOT reveal them): " + "; ".join(planned.expected_points))
    if last_answer:
        lines.append(f"The student just said: \"{last_answer[:1500]}\"")
    return trim(llm.say(SYSTEM.format(language=config.LANGUAGE_NAME), "\n".join(lines)))


def trim(text: str) -> str:
    """Spoken lines stay short even when the model rambles: a bridge sentence and the question, nothing between."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if p.strip()]
    if len(parts) <= 2:
        return " ".join(parts)
    question = next((p for p in reversed(parts) if p.endswith("?")), parts[-1])
    return f"{parts[0]} {question}"
