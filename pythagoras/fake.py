"""Offline stand-in for Claude (PYTHAGORAS_FAKE_LLM=1): deterministic outputs so tests and the UI run without a key."""
import json
from typing import Type

from .models import (Analysis, Anchored, BloomQuestion, Evaluation, Evidence, InterviewPlan, InterviewReport,
                     Topic, TopicResult)

TOPICS = [("problem", "Problem framing", "high"), ("method", "Method and design choices", "high"),
          ("results", "Results and evaluation", "medium")]


def parse(schema: Type, content):
    if schema is InterviewPlan:
        return InterviewPlan(topics=[
            Topic(id=tid, title=title, claim=f"The deliverable explains its {title.lower()}.",
                  anchor=f"section {i + 1}", priority=prio, time_budget_s=150,
                  questions=[BloomQuestion(level=lv, question=f"[L{lv}] Tell me about the {title.lower()}.",
                                           expected_points=["a specific detail"]) for lv in (2, 3, 4, 5)])
            for i, (tid, title, prio) in enumerate(TOPICS)],
            analysis=Analysis(summary="A student project (offline placeholder analysis).",
                              strengths=[Anchored(text="Clear structure", anchor="section 1")],
                              weak_spots=[Anchored(text="Evaluation is thin", anchor="section 3")],
                              objectives_coverage=["LO1: covered"]))
    if schema is Evaluation:
        answer = json.loads(content).get("student_answer", "")
        words = len(answer.split())
        verdict = "dont_know" if "know" in answer.lower() else "solid" if words >= 8 else "partial" if words >= 3 else "weak"
        return Evaluation(verdict=verdict, covered_points=[], missing_points=[], note=f"Fake judgement: {verdict}.")
    if schema is InterviewReport:
        data = json.loads(content)
        answers = [t for t in data["transcript"] if t.get("student") and t.get("topic_id")]
        return InterviewReport(
            summary="Offline placeholder report: the student answered the interview questions.",
            ownership="mixed",
            topics=[TopicResult(topic_id=t["topic_id"], title=t["title"], level_reached=t["level_reached"],
                                assessment="Placeholder assessment.",
                                evidence=[Evidence(quote=" ".join(a["student"].split()[:8]), t_s=a["t_s"],
                                                   note="first answer on this topic")
                                          for a in answers if a["topic_id"] == t["topic_id"]][:1])
                    for t in data["topics"]],
            strengths=["Answers on topic"], concerns=["Placeholder: run with a real key"],
            suggested_questions=["Why did you choose this method?"])
    raise TypeError(f"fake.parse: unsupported schema {schema.__name__}")


def say(prompt: str) -> str:
    planned = next((ln.split(": ", 1)[1] for ln in prompt.splitlines() if ln.startswith("Planned question: ")), None)
    if "Thank the team" in prompt:
        return "Thank you, that's the end of our conversation. Your professor will receive a summary."
    return planned or "Hello! Could you tell me in a few sentences what your project does?"
