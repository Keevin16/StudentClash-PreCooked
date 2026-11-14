"""The 1-on-1 interview engine. Stateless between requests: the API rebuilds it from the stored state.

    step = Interview(plan, state).start()            # opening question
    step = Interview(plan, state).answer(text, dur)  # evaluate (reasoner) -> rules -> next question (talker)

Rules (deterministic, the LLM only judges single answers):
- every topic starts at Bloom level 2 (Understand); a solid answer climbs one level, up to 5 (Evaluate)
- the first non-solid answer at a level gets one second chance: a probe (partial) or a scaffold hint (weak)
- a second non-solid answer, the topic's time budget, or reaching level 5 closes the topic
- topics go in plan order (priority); when time is nearly up or topics run out: wrap up.

Latency: most answers are solid, and what a solid answer leads to is known before the judgement. So while the
judge works, the talker already phrases that follow-up; it is used if the verdict agrees, discarded otherwise."""
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Optional

from . import config, supervisor, talker
from .models import (BLOOM, MAX_LEVEL, MIN_LEVEL, Evaluation, InterviewPlan, InterviewState, Move, Step, Topic,
                     TopicState, Turn)

log = logging.getLogger("pythagoras.engine")
WRAP_MARGIN_S = 30  # start closing this long before the end
# fixed: closing must work even when the LLM is unavailable
CLOSING = {"it": "Grazie, la nostra conversazione finisce qui. Il vostro docente riceverà un riepilogo di quello che "
                 "ci siamo detti. In bocca al lupo per il progetto!",
           "en": "Thank you, that's the end of our conversation. Your professor will receive a summary of what we "
                 "discussed. Good luck with your project!"}
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="talker")


def closing() -> str:
    return CLOSING.get(config.LANGUAGE, CLOSING["en"])


def new_state(plan: InterviewPlan) -> InterviewState:
    return InterviewState(topics=[TopicState(id=t.id) for t in plan.topics])


class Interview:
    def __init__(self, plan: InterviewPlan, state: InterviewState, clock: Callable[[], float] = time.time):
        self.plan, self.state, self.clock = plan, state, clock

    # ---------- public ----------

    def start(self) -> Step:
        self.state = new_state(self.plan)
        self.state.started_at = self.clock()
        move = Move(kind="opening", intent="Greet the team in one short sentence (you are Pythagoras, this is a short chat about "
                    "their own project, whoever worked on a part answers about it), then ask them to summarise in a "
                    "few sentences what they built and the decision they are most proud of.")
        return self._ask(move)

    def answer(self, text: str, duration_s: Optional[float] = None) -> Step:
        turn = self.state.turns[-1]
        if self.state.finished:
            raise ValueError("The interview is over")
        if turn.answer is not None:
            raise ValueError("This question was already answered")
        if self.elapsed() >= self.plan.duration_s:  # time is over: save the answer, close without any LLM call
            return self.finish(text, duration_s)
        turn.answer, turn.answer_s = text.strip(), duration_s
        move = turn.move

        guess: Optional[Move] = None
        ready: Optional[Future] = None
        t0 = t1 = time.monotonic()
        if move.topic_id:
            ts = self._ts(move.topic_id)
            ts.spent_s += self.clock() - self.state.started_at - turn.t_s
            if config.SPECULATE and text.strip():
                guess = self._capped(self._if_solid(turn))
                ready = _pool.submit(talker.phrase, self.plan, self._topic_of(guess), guess, text)
            turn.evaluation = supervisor.evaluate(self.plan, self._topic(move.topic_id), move, turn.question, text)
            nxt = self._after_answer(ts, turn)
            t1 = time.monotonic()
        else:  # opening: no judgement, just context for the talker
            nxt = self._open_next()

        nxt = self._capped(nxt)
        question = None
        if ready is not None and nxt == guess:  # the verdict agrees with the guess: the line is (almost) ready
            try:
                question = ready.result()
            except Exception as e:  # phrase it again below, on the normal path
                log.warning("speculative talker failed: %s", e)
        reused = question is not None
        step = self._ask(nxt, last_answer=text, question=question)
        log.info("turn: judge %.1fs (%s), talker +%.1fs%s -> %s L%s", t1 - t0,
                 turn.evaluation.verdict if turn.evaluation else "-", time.monotonic() - t1,
                 " (phrased while judging)" if reused else "", nxt.kind, nxt.level)
        step.transcript = text
        return step

    def finish(self, text: Optional[str] = None, duration_s: Optional[float] = None) -> Step:
        """End now (time over, or the student/LLM can't go on). Keeps the pending answer; no LLM calls."""
        if not self.state.finished:
            turn = self.state.turns[-1] if self.state.turns else None
            if turn and turn.answer is None and text and text.strip():
                turn.answer, turn.answer_s = text.strip(), duration_s
            for t in self.state.topics:
                if t.status == "open":
                    t.status = "closed"
            self.state.turns.append(Turn(t_s=round(self.elapsed(), 1), move=Move(kind="wrap_up"), question=closing()))
            self.state.finished = True
        return self._step(self.state.turns[-1])

    def current(self) -> Step:
        """The question waiting for an answer (to resume after a reload); no LLM calls."""
        return self._step(self.state.turns[-1])

    def elapsed(self) -> float:
        return self.clock() - (self.state.started_at or self.clock())

    # ---------- rules ----------

    def _after_answer(self, ts: TopicState, turn: Turn) -> Move:
        ev, topic = turn.evaluation, self._topic(ts.id)
        over_budget = ts.spent_s >= topic.time_budget_s
        if ev.verdict == "solid":
            ts.level, ts.misses = max(ts.level, ts.current), 0
            if ts.current >= MAX_LEVEL or over_budget:
                return self._close(ts)
            ts.current += 1
            return Move(kind="ask", topic_id=ts.id, level=ts.current,
                        intent="Go one step deeper on the same topic with the planned question for this level.")
        ts.misses += 1
        if ts.misses == 1 and not over_budget:
            if ev.verdict == "partial":
                return Move(kind="probe", topic_id=ts.id, level=ts.current,
                            intent="The answer was incomplete. Ask a short follow-up that pushes on what is "
                                   "missing, without revealing it.")
            return Move(kind="scaffold", topic_id=ts.id, level=ts.current,
                        intent="The team struggled. Give a small hint pointing to the relevant part of their "
                               "own deliverable, then ask a simpler version of the question.")
        return self._close(ts)

    def _if_solid(self, turn: Turn) -> Move:
        """The move a solid answer leads to, worked out on a copy: the real state is not touched."""
        twin = Interview(self.plan, self.state.model_copy(deep=True), self.clock)
        last = twin.state.turns[-1]
        last.evaluation = Evaluation(verdict="solid", covered_points=[], missing_points=[], note="")
        return twin._after_answer(twin._ts(turn.move.topic_id), last)

    def _capped(self, move: Move) -> Move:
        """Time nearly over: whatever the rules said, close."""
        if self.elapsed() >= self.plan.duration_s - WRAP_MARGIN_S and move.kind != "wrap_up":
            return self._wrap("Time is up.")
        return move

    def _close(self, ts: TopicState) -> Move:
        ts.status = "closed"
        return self._open_next()

    def _open_next(self) -> Move:
        ts = next((t for t in self.state.topics if t.status == "pending"), None)
        if ts is None:
            return self._wrap("All topics covered.")
        ts.status, ts.current, ts.misses = "open", MIN_LEVEL, 0
        first = all(t.status == "pending" or t.id == ts.id for t in self.state.topics)
        return Move(kind="ask" if first else "next_topic", topic_id=ts.id, level=MIN_LEVEL,
                    intent="Introduce this topic of their project (mention where it is in the deliverable) "
                           "and ask the planned question." if first else
                           "Briefly move on to a new topic of their project (mention where it is in the "
                           "deliverable) and ask the planned question.")

    def _wrap(self, why: str) -> Move:
        for t in self.state.topics:
            if t.status == "open":
                t.status = "closed"
        return Move(kind="wrap_up", intent=f"{why} Thank the team warmly, say the conversation is over and "
                                            "that their professor will receive a summary. Ask nothing.")

    # ---------- helpers ----------

    def _ask(self, move: Move, last_answer: str = "", question: Optional[str] = None) -> Step:
        question = question or talker.phrase(self.plan, self._topic_of(move), move, last_answer)
        turn = Turn(t_s=round(self.elapsed(), 1), move=move, question=question)
        self.state.turns.append(turn)
        if move.kind == "wrap_up":  # the closing line expects no answer
            self.state.finished = True
        return self._step(turn)

    def _step(self, turn: Turn) -> Step:
        move, ids = turn.move, [t.id for t in self.plan.topics]
        topic = self._topic(move.topic_id) if move.topic_id else None
        return Step(kind=move.kind, question=turn.question, topic_title=topic.title if topic else None,
                    level=move.level, level_name=BLOOM.get(move.level), duration_s=self.plan.duration_s,
                    topic_index=ids.index(move.topic_id) + 1 if move.topic_id else 0, topics_total=len(ids),
                    elapsed_s=round(self.elapsed(), 1), done=self.state.finished,
                    levels={t.id: t.level for t in self.state.topics})

    def _topic_of(self, move: Move) -> Optional[Topic]:
        return self._topic(move.topic_id) if move.topic_id else None

    def _topic(self, tid: str) -> Topic:
        return next(t for t in self.plan.topics if t.id == tid)

    def _ts(self, tid: str) -> TopicState:
        return next(t for t in self.state.topics if t.id == tid)
