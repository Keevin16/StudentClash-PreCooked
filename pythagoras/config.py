"""Settings from the environment (.env is loaded by the app at startup)."""
import os
import secrets
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env reader: KEY=VALUE lines, existing environment wins."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.split(" #")[0].strip())


if os.environ.get("PYTHAGORAS_NO_DOTENV") != "1":
    load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATA_DIR = Path(_env("PYTHAGORAS_DATA_DIR", "data"))
PUBLIC_URL = _env("PYTHAGORAS_PUBLIC_URL", "http://localhost:8000").rstrip("/")
DURATION_S = int(_env("PYTHAGORAS_DURATION_S", "600"))
LANGUAGE = _env("PYTHAGORAS_LANGUAGE", "en")  # en | it: what Pythagoras speaks, hears and writes
LANGUAGE_NAME = {"it": "Italian", "en": "English"}.get(LANGUAGE, LANGUAGE)
VOICE = _env("PYTHAGORAS_VOICE", "auto")  # auto (local models if installed, else the browser's speech) | local | browser
CAMERA = _env("PYTHAGORAS_CAMERA", "1") == "1"  # webcam on and visible during the interview; nothing is recorded or sent
SPECULATE = _env("PYTHAGORAS_SPECULATE", "1") == "1"  # phrase the "solid answer" follow-up while the judge works
# demo rules (engine._demo_rule): a good first answer on the weights topic climbs to level 3; "I don't know"
# gets one retry, a second one moves on. On for now; PYTHAGORAS_DEMO_RULES=0 turns them off.
DEMO_RULES = _env("PYTHAGORAS_DEMO_RULES", "1") == "1"

# Two roles: the reasoner (plan, Bloom judgement of each answer, report) and the fast talker.
GEMINI_API_KEY = _env("GEMINI_API_KEY")
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
PROVIDER = _env("PYTHAGORAS_PROVIDER") or ("anthropic" if _env("ANTHROPIC_API_KEY") else "openrouter" if OPENROUTER_API_KEY
                                        else "gemini" if GEMINI_API_KEY else "anthropic")
_DEFAULTS = {"anthropic": ("claude-sonnet-5-5", "claude-haiku-5-5"),
             # paid per token, no daily quota. Claude: some OpenRouter accounts' guardrails block Google/OpenAI models
             "openrouter": ("anthropic/claude-sonnet-5.5", "anthropic/claude-haiku-5.5"),
             "gemini": ("gemini-3.5-flash", "gemini-3.5-flash-lite")}
# Per-provider overrides win (PYTHAGORAS_GEMINI_REASONER_MODEL...), so switching provider never keeps a wrong model id
REASONER_MODEL = _env(f"PYTHAGORAS_{PROVIDER.upper()}_REASONER_MODEL") or _env("PYTHAGORAS_REASONER_MODEL") or _DEFAULTS[PROVIDER][0]
TALKER_MODEL = _env(f"PYTHAGORAS_{PROVIDER.upper()}_TALKER_MODEL") or _env("PYTHAGORAS_TALKER_MODEL") or _DEFAULTS[PROVIDER][1]
# Judges every answer, live. Gemini: the lite model (the free tier allows ~20 requests a DAY on Flash: enough for
# plans and reports, not for a judgement per answer). Claude: the reasoner at low effort.
JUDGE_MODEL = _env("PYTHAGORAS_JUDGE_MODEL") or (REASONER_MODEL if PROVIDER == "anthropic" else TALKER_MODEL)
TOPICS = int(_env("PYTHAGORAS_TOPICS", "3"))  # topics per interview
FAKE_LLM = _env("PYTHAGORAS_FAKE_LLM") == "1"  # offline stub: tests and UI work without a key

PROFESSOR_PASSWORD = _env("PYTHAGORAS_PROFESSOR_PASSWORD")  # empty (default): the professor pages are open, no login
SECRET = _env("PYTHAGORAS_SECRET") or secrets.token_hex(16)  # signs the professor cookie

SMTP_HOST = _env("SMTP_HOST")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USER = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")
SMTP_FROM = _env("SMTP_FROM", SMTP_USER or "pythagoras@localhost")
