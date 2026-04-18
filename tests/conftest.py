"""
Pytest configuration.

`src/` imports `streamlit as st` in several modules. The bits we unit-test
are pure (no network, no widgets) but the import chain still pulls Streamlit
in — that is fine when streamlit is installed. If not, tests that only
exercise pure helpers can still run by skipping streamlit-dependent modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable as `from src...` without needing a pip install.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
