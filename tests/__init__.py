"""Test package for the Personal Finance Agent.

Adds the ``src`` directory to ``sys.path`` so the test suite can import
``personal_finance_agent`` without an editable install. This keeps the first
deterministic slice dependency-free while it is still a workspace-local package.

Run with (from the repository root):

    uv run python -m unittest discover -s tests -t . -v
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))