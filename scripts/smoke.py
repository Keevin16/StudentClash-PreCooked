"""End-to-end check against a running server, with a synthetic student (cases/ffnn) whose answers are spoken
by Kokoro and sent through the same microphone WebSocket the page uses. Prints the latency of every stage.

    python -m pythagoras serve            # in another terminal
    python scripts/smoke.py [--url http://localhost:8000] [--text]     # --text: skip the voice path"""
import argparse
import asyncio
import base64
import io
import json
import time
import wave
from pathlib import Path

import httpx

CASE = Path(__file__).resolve().parent.parent / "cases" / "ffnn"
ANSWERS = [
    "I built a small feed-forward neural network from scratch in NumPy, with one hidden layer, and trained it on "
    "a two dimensional binary classification dataset. The decision I am most proud of is writing backpropagation by hand.",
    "In the code the first weight matrix starts at zero and the second one is random with a small scale. With all "
    "zeros the hidden neurons would compute the same thing and get the same gradient, and only the random second "
    "layer breaks that symmetry. The report says Xavier, which is a mistake on my side.",
    "Honestly, I am not sure. I picked the learning rate by looking at which value gave the best accuracy on the test set.",
    "I don't know.",
]


async def speak(c: httpx.AsyncClient, text: str):
    """-> (seconds to the first audio chunk, int16 PCM at 24 kHz)."""
    import numpy as np
    t, first, pcm = time.monotonic(), None, []
    async with c.stream("POST", "/api/voice/speak", json={"text": text}) as r:
        r.raise_for_status()
        async for line in r.aiter_lines():
            if not line.strip():
                continue
            first = first or time.monotonic() - t
            with wave.open(io.BytesIO(base64.b64decode(json.loads(line)["audio"]))) as w:
                pcm.append(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16))
    return first, np.concatenate(pcm)


async def say_into_mic(ws, pcm24, epoch: int):
    """Plays the student's answer into the WebSocket at 16 kHz, then silence. -> (transcript, timings)."""
    import numpy as np
    x = np.interp(np.arange(0, len(pcm24), 1.5), np.arange(len(pcm24)), pcm24.astype(np.float32)).astype("<i2")
    x = np.concatenate([np.zeros(8000, "<i2"), x, np.zeros(16000 * 4, "<i2")])
    await ws.send(json.dumps({"type": "listen", "enabled": True, "epoch": epoch}))
    speech_end = (len(x) - 16000 * 4) / 16000
    out = {}

    async def feed():
        for i in range(0, len(x), 320):  # real time: the end-of-turn delay is measured against the audio clock
            await ws.send(x[i:i + 320].tobytes())
            await asyncio.sleep(0.02)
        await ws.send(json.dumps({"type": "finish"}))  # the "I'm done" button: the server never ends a turn on its own

    feeder, t0 = asyncio.ensure_future(feed()), time.monotonic()
    try:
        while True:
            m = json.loads(await asyncio.wait_for(ws.recv(), 60))
            now = time.monotonic() - t0
            if m["type"] == "turn_end":
                out["end_of_turn_after_speech_s"] = round(now - speech_end, 2)
                t_end = time.monotonic()
            elif m["type"] == "transcript":
                out["stt_s"] = round(time.monotonic() - t_end, 2)
                return m["text"], out
            elif m["type"] in ("empty", "error"):
                return "", {**out, "problem": m}
    finally:
        feeder.cancel()


async def main(url: str, text_only: bool) -> None:
    import websockets
    async with httpx.AsyncClient(base_url=url, timeout=120) as c:
        # professor: assignment with the course notes
        r = await c.post("/api/prof/login", json={"password": __import__("os").environ.get("PYTHAGORAS_PROFESSOR_PASSWORD", "")})
        r.raise_for_status()
        r = await c.post("/api/prof/assignments", data={
            "title": "Project 1 - A feed-forward network from scratch", "course": "Introduction to Deep Learning",
            "description": "Implement a small MLP from scratch in NumPy and write a short report.",
            "objectives": "LO1 Explain forward propagation\nLO2 Implement backpropagation\nLO3 Justify initialisation and "
                          "learning rate\nLO4 Evaluate correctly and recognise overfitting"},
            files=[("materials", ("ffnn-notes.md", (CASE / "course/ffnn-notes.md").read_bytes()))])
        aid = r.json()["id"]
        # student: deliverable
        r = await c.post("/api/submissions", data={"assignment_id": aid, "name": "Marco Bianchi", "email": "marco@example.com"},
                         files=[("files", (n, (CASE / "deliverable" / n).read_bytes())) for n in ("report.pdf", "mlp.py")])
        r.raise_for_status()
        sid = r.json()["id"]
        token = (await c.get(f"/api/prof/assignments/{aid}")).json()["submissions"][0]["invite_url"].rsplit("/", 1)[1]
        t = time.monotonic()
        while (info := (await c.get(f"/api/interview/{token}")).json())["status"] == "preparing":
            await asyncio.sleep(2)
        print(f"plan: {info['status']} in {time.monotonic() - t:.0f}s, {info['topics_total']} topics, voice={info['voice']}")
        assert info["status"] == "ready", info
        voice = info["voice"] == "local" and not text_only
        if voice:
            (await c.post("/api/voice/warmup")).raise_for_status()
            ws = await websockets.connect(url.replace("http", "ws", 1) + f"/api/voice/stream?token={token}")
            assert json.loads(await ws.recv())["type"] == "ready"

        t = time.monotonic()
        step = (await c.post(f"/api/interview/{token}/start")).json()
        print(f"\nPYTHAGORAS ({time.monotonic() - t:.2f}s): {step['question']}")
        for i, answer in enumerate(ANSWERS, 1):
            row = {}
            if voice:
                row["question_first_audio_s"] = round((await speak(c, step["question"]))[0], 2)
                _, pcm = await speak(c, answer)
                heard, timing = await say_into_mic(ws, pcm, i)
                row.update(timing)
                answer = heard or answer
            print(f"STUDENT: {answer}")
            t = time.monotonic()
            r = await c.post(f"/api/interview/{token}/answer", json={"text": answer, "duration_s": None})
            r.raise_for_status()
            step = r.json()
            row["judge_and_talker_s"] = round(time.monotonic() - t, 2)
            print(f"   {row}\nPYTHAGORAS [{step['kind']} L{step['level']}]: {step['question']}")
            if step["done"]:
                break
        if not step["done"]:
            step = (await c.post(f"/api/interview/{token}/finish", json={})).json()
        t = time.monotonic()
        while not (d := (await c.get(f"/api/prof/submissions/{sid}")).json())["report"] and time.monotonic() - t < 180:
            await asyncio.sleep(3)
        rep = d["report"]
        print(f"\nreport in {time.monotonic() - t:.0f}s:", (rep or {}).get("ownership"), "-", (rep or {}).get("summary", "NOT READY")[:300])
        if rep:
            print("levels:", {x["title"]: x["level_reached"] for x in rep["topics"]}, "| unverified quotes:", len(rep["unverified_quotes"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--text", action="store_true")
    a = p.parse_args()
    asyncio.run(main(a.url.rstrip("/"), a.text))
