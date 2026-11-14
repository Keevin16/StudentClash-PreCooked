import os
import tempfile

# Before any pythagoras import: offline LLM, throwaway data dir, no .env, no voice models loaded at startup.
os.environ.update(PYTHAGORAS_NO_DOTENV="1", PYTHAGORAS_FAKE_LLM="1", PYTHAGORAS_DATA_DIR=tempfile.mkdtemp(prefix="pythagoras-test-"),
                  PYTHAGORAS_PROFESSOR_PASSWORD="pw", PYTHAGORAS_DURATION_S="600", PYTHAGORAS_VOICE="browser",
                  PYTHAGORAS_DEMO_RULES="0")  # base rules; tests/test_demo_rules.py turns the demo rules on
