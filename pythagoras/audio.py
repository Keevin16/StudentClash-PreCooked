"""Local voice models (Apple Silicon): Silero VAD + Smart Turn v3 for the end of turn, Whisper (MLX) to
transcribe, Kokoro to speak. Everything loads lazily, so this module imports with numpy only.

End of turn = Silero says the frames are silence + Smart Turn v3 decides, after a short pause, whether the
sentence is finished or the student is just thinking ("so... uhm"); a longer silence is the safety net."""
import logging
import os
import re
from collections import deque
from pathlib import Path
from typing import Callable, Iterator, Optional

import numpy as np

from . import config

log = logging.getLogger("pythagoras.audio")

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))  # models live next to the project

SAMPLE_RATE = 16000  # what the browser sends, and what Whisper / Smart Turn / Silero expect
TTS_SAMPLE_RATE = 24000  # Kokoro
SILENCE_S = float(os.environ.get("PYTHAGORAS_SILENCE_S", 2.5))  # safety net when Smart Turn says "not finished"
# Ask Smart Turn after this pause. Measured: at 0.7 s it ends the turn in the gap between two finished sentences;
# at 1.0 s people who pause to breathe keep the floor, and a finished answer still gets its reply quickly.
SMART_TURN_SILENCE_S = float(os.environ.get("PYTHAGORAS_SMART_TURN_SILENCE_S", 1.0))
MIN_SPEECH_S = 0.3  # shorter bursts (cough, "mm") are not an answer
VAD_THRESHOLD = 0.5
SMART_TURN = os.environ.get("PYTHAGORAS_SMART_TURN", "smart-turn-v3.2-cpu.onnx")  # file in the HF repo, local path, or "off"
SMART_TURN_REPO = "pipecat-ai/smart-turn-v3"
SMART_TURN_THRESHOLD = 0.5
SMART_TURN_WINDOW_S = 8  # the model sees the last 8 s
WHISPER_MODEL = os.environ.get("PYTHAGORAS_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
KOKORO_LANG = {"it": "i", "en": "a"}.get(config.LANGUAGE, "a")
KOKORO_VOICE = os.environ.get("PYTHAGORAS_KOKORO_VOICE", "im_nicola" if config.LANGUAGE == "it" else "af_heart")
KOKORO_SPEED = float(os.environ.get("PYTHAGORAS_KOKORO_SPEED", 1.0))


# ---------- voice activity ----------

class SileroVad:
    """Stateful, one per connection. Silero wants 512-sample chunks at 16 kHz; frames arrive in 20 ms pieces."""
    CHUNK = 512

    def __init__(self) -> None:
        from silero_vad import load_silero_vad
        self.model = load_silero_vad(onnx=True)
        self.rest = np.zeros(0, dtype=np.int16)
        self.speech = False

    def __call__(self, pcm: np.ndarray) -> bool:
        import torch
        self.rest = np.concatenate([self.rest, pcm])
        while len(self.rest) >= self.CHUNK:
            chunk, self.rest = self.rest[:self.CHUNK], self.rest[self.CHUNK:]
            x = torch.from_numpy(chunk.astype(np.float32) / 32768.0)
            self.speech = self.model(x, SAMPLE_RATE).item() > VAD_THRESHOLD
        return self.speech


# ---------- end of turn ----------

class TurnDetector:
    """Feed 16 kHz int16 frames; returns the whole utterance when the speaker has finished.

    After SMART_TURN_SILENCE_S of silence Smart Turn decides; if it says "still thinking" (or is
    unavailable) the turn ends only after SILENCE_S, so a pause with "uhm" is never cut."""

    def __init__(self, is_speech: Optional[Callable[[np.ndarray], bool]] = None,
                 smart_turn: Optional[Callable[[np.ndarray], Optional[bool]]] = None,
                 silence_s: float = SILENCE_S, pre_roll_s: float = 0.25) -> None:
        self.is_speech = is_speech or SileroVad()
        self.smart_turn = smart_turn or smart_turn_complete
        self.silence_limit = silence_s
        self.pre_roll: deque = deque()  # audio just before the first speech frame, so the first syllable is kept
        self.pre_roll_samples = int(pre_roll_s * SAMPLE_RATE)
        self.buf: list = []
        self.speech_s = 0.0
        self.silence_s = 0.0
        self.asked_smart_turn = False

    def push(self, pcm: np.ndarray) -> Optional[np.ndarray]:
        dur = len(pcm) / SAMPLE_RATE
        if self.is_speech(pcm):
            if not self.buf and self.pre_roll:
                self.buf.extend(self.pre_roll)
                self.pre_roll.clear()
            self.buf.append(pcm)
            self.speech_s += dur
            self.silence_s, self.asked_smart_turn = 0.0, False
            return None
        if not self.buf:
            if self.pre_roll_samples:
                self.pre_roll.append(pcm.copy())
                while sum(len(x) for x in self.pre_roll) > self.pre_roll_samples:
                    self.pre_roll.popleft()
            return None
        self.buf.append(pcm)
        self.silence_s += dur
        done = self.silence_s >= self.silence_limit
        if not done and self.silence_s >= SMART_TURN_SILENCE_S and not self.asked_smart_turn:
            self.asked_smart_turn = True
            done = self.speech_s >= MIN_SPEECH_S and self.smart_turn(np.concatenate(self.buf)) is True
        if not done:
            return None
        return self.take()

    def take(self) -> Optional[np.ndarray]:
        """Close the utterance now (silence, or the student pressed "I'm done"). None if it was not speech."""
        audio, speech_s = (np.concatenate(self.buf) if self.buf else None), self.speech_s
        self.buf, self.speech_s, self.silence_s, self.asked_smart_turn = [], 0.0, 0.0, False
        return audio if audio is not None and speech_s >= MIN_SPEECH_S else None


class SmartTurn:
    """Smart Turn v3 (ONNX, BSD-2): probability that the speaker has finished, from audio only.
    Same preprocessing as pipecat-ai/smart-turn inference.py."""

    def __init__(self, model: str = SMART_TURN) -> None:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from transformers import WhisperFeatureExtractor
        path = model if Path(model).exists() else hf_hub_download(SMART_TURN_REPO, model)
        so = ort.SessionOptions()
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(path, sess_options=so)
        self.features = WhisperFeatureExtractor(chunk_length=SMART_TURN_WINDOW_S)

    def probability(self, pcm: np.ndarray) -> float:
        n = SMART_TURN_WINDOW_S * SAMPLE_RATE
        x = pcm[-n:].astype(np.float32) / 32768.0
        f = self.features(x, sampling_rate=SAMPLE_RATE, return_tensors="np", padding="max_length",
                          max_length=n, truncation=True, do_normalize=True)
        feats = f.input_features.squeeze(0).astype(np.float32)[None]
        return float(self.session.run(None, {"input_features": feats})[0][0].item())


_smart: Optional[SmartTurn] = None
_smart_failed = False


def smart_turn_complete(audio: np.ndarray) -> Optional[bool]:
    """True = sentence finished, False = still thinking, None = not available (the silence safety net decides)."""
    global _smart, _smart_failed
    if SMART_TURN == "off" or _smart_failed:
        return None
    try:
        if _smart is None:
            _smart = SmartTurn()
        return _smart.probability(audio) > SMART_TURN_THRESHOLD
    except Exception as e:
        _smart_failed = True
        log.warning("Smart Turn unavailable (%s): end of turn after %.1f s of silence", e, SILENCE_S)
        return None


# ---------- speech to text / text to speech ----------

def transcribe(audio: np.ndarray, glossary: str = "") -> str:
    """`glossary`: the project's own terms (from the interview plan), so Whisper spells them right."""
    import mlx_whisper  # Apple Silicon only
    out = mlx_whisper.transcribe(audio.astype(np.float32) / 32768.0, path_or_hf_repo=WHISPER_MODEL,
                                 initial_prompt=glossary or None, language=config.LANGUAGE, task="transcribe",
                                 temperature=0.0, condition_on_previous_text=False,
                                 hallucination_silence_threshold=1.0)
    return out["text"].strip()


def sentences(text: str) -> list:
    """Split what Pythagoras says into sentences: each is synthesized on its own, so the first one (a short
    bridge) starts playing in well under a second while the question is still being generated."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text.strip()) if p.strip()]
    if parts and len(parts[0]) > 110:  # a long opening sentence: start speaking at its first comma instead
        head, comma, tail = parts[0].partition(", ")
        if comma and 20 <= len(head) <= 90:
            parts[:1] = [head + ",", tail]
    out: list = []
    for p in parts:  # glue fragments like "Ok." to the next sentence: too short to sound natural alone
        if out and len(out[-1]) < 12:
            out[-1] += " " + p
        else:
            out.append(p)
    return out


_kokoro = None


def synthesize_stream(text: str) -> Iterator[np.ndarray]:
    """int16 mono chunks at TTS_SAMPLE_RATE, one per sentence."""
    global _kokoro
    if _kokoro is None:
        from kokoro import KPipeline
        _kokoro = KPipeline(lang_code=KOKORO_LANG, device="cpu", repo_id="hexgrad/Kokoro-82M")  # measured: CPU beats MPS here
    for sentence in sentences(text):
        for _, _, audio in _kokoro(sentence, voice=KOKORO_VOICE, speed=KOKORO_SPEED):
            if audio is not None:
                yield (np.clip(np.asarray(audio), -1, 1) * 32767).astype(np.int16)


def warm_up() -> None:
    """Load (and on the first run download) every model before the interview: cold, each first call takes seconds."""
    list(synthesize_stream("Hello, I am Pythagoras. Let's talk about your project."))
    transcribe(np.zeros(SAMPLE_RATE, dtype=np.int16))
    smart_turn_complete(np.zeros(SAMPLE_RATE, dtype=np.int16))
    SileroVad()
