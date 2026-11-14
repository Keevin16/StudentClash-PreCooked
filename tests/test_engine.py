from pythagoras import fake
from pythagoras.engine import Interview, new_state
from pythagoras.models import InterviewPlan


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def plan() -> InterviewPlan:
    return fake.parse(InterviewPlan, [])


SOLID = "a long specific and correct answer about my own project choices"


def test_solid_answers_climb_to_evaluate_then_move_on():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    assert iv.start().kind == "opening"
    step = iv.answer("I built a classifier")
    assert (step.topic_index, step.level) == (1, 2)
    for level in (3, 4, 5):
        clock.t += 10
        step = iv.answer(SOLID)
        assert step.level == level and step.topic_index == 1
    step = iv.answer(SOLID)
    assert step.topic_index == 2 and step.kind == "next_topic" and step.levels["problem"] == 5


def test_two_misses_close_the_topic_at_the_level_reached():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    iv.answer("intro")
    iv.answer(SOLID)                       # L2 solid -> L3
    assert iv.answer("no").kind == "scaffold"
    step = iv.answer("I don't know")
    assert step.topic_index == 2 and step.levels["problem"] == 2


def test_partial_gets_a_probe():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    iv.answer("intro")
    assert iv.answer("it uses trees").kind == "probe"


def test_time_up_wraps_and_finishes():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    clock.t += 600
    step = iv.answer("intro")
    assert step.kind == "wrap_up" and step.done and iv.state.finished


def test_all_topics_done_wraps():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    step = iv.answer("intro")
    while not step.done:
        step = iv.answer("I don't know")
    assert step.kind == "wrap_up"
    assert all(t.status == "closed" for t in iv.state.topics)


def test_time_over_closes_without_any_llm_call(monkeypatch):
    from pythagoras import supervisor, talker
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    iv.answer("intro")
    boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("quota"))
    monkeypatch.setattr(supervisor, "evaluate", boom)
    monkeypatch.setattr(talker, "phrase", boom)
    clock.t += 601
    step = iv.answer("my late answer")
    assert step.done and step.kind == "wrap_up"
    assert iv.state.turns[-2].answer == "my late answer"


def test_finish_keeps_the_unsent_answer():
    clock, p = Clock(), plan()
    iv = Interview(p, new_state(p), clock)
    iv.start()
    iv.answer("intro")
    step = iv.finish("half an answer", 4.0)
    assert step.done and iv.state.finished
    assert iv.state.turns[-2].answer == "half an answer"
    assert all(t.status != "open" for t in iv.state.topics)
