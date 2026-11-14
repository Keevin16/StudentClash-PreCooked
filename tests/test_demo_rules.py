import pytest

from pythagoras import config, fake
from pythagoras.engine import Interview, new_state
from pythagoras.models import InterviewPlan

SOLID = "a long specific and correct answer about my own project choices"


@pytest.fixture(autouse=True)
def demo_rules(monkeypatch):
    monkeypatch.setattr(config, "DEMO_RULES", True)


def interview(first_topic=None) -> Interview:
    p = fake.parse(InterviewPlan, [])
    if first_topic:
        p.topics[0].id, p.topics[0].title = first_topic
    iv = Interview(p, new_state(p), lambda: 1000.0)
    iv.start()
    iv.answer("intro")                                   # -> topic 1, level 2
    return iv


def test_dont_know_gets_one_retry_then_moves_on():
    iv = interview()
    step = iv.answer("I don't know")
    assert (step.kind, step.topic_index, step.level) == ("scaffold", 1, 1)   # retry one level lower
    step = iv.answer("I don't know")
    assert step.kind == "next_topic" and step.topic_index == 2


def test_dont_know_lowers_the_next_question_and_a_good_answer_climbs_back():
    iv = interview()
    iv.answer(SOLID)                                     # L2 solid -> L3
    assert iv.answer("I don't know").level == 2          # retry at L2
    step = iv.answer(SOLID)
    assert (step.kind, step.level) == ("ask", 3) and step.levels[iv.plan.topics[0].id] == 2


def test_dont_know_after_a_weak_answer_still_gets_its_retry():
    iv = interview()
    assert iv.answer("no").kind == "scaffold"           # weak -> hint (normal rule)
    assert iv.answer("I don't know").kind == "scaffold"  # first "I don't know": one retry
    assert iv.answer("I don't know").topic_index == 2    # second in a row: next topic


def test_first_answer_on_weights_climbs_to_level_3_even_if_partial():
    iv = interview(("init", "Weight initialisation"))
    step = iv.answer("zeros for W1")                     # 3 words: the fake judge says partial
    assert iv.state.turns[-2].evaluation.verdict == "partial"
    assert (step.kind, step.topic_index, step.level) == ("ask", 1, 3)


def test_dont_know_on_weights_does_not_climb():
    iv = interview(("init", "Weight initialisation"))
    step = iv.answer("I don't know")
    assert (step.kind, step.level) == ("scaffold", 1)
    iv = interview(("init", "Weight initialisation"))
    iv.state.turns[-1].answer = None
    assert iv.answer("hmm, not sure honestly").level != 3   # a short "not sure" is no answer either


def test_other_topics_keep_the_normal_rules():
    iv = interview()
    assert iv.answer("zeros for W1").kind == "probe"     # partial on a topic not about weights
