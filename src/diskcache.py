"""
Disk-persistent cache for indicator data.

Streamlit's `@st.cache_data` is in-memory only, so every container
restart on Streamlit Cloud forces the first visitor of the day to
wait through every fetch again. This module adds a second layer that
survives restarts:

  * Keyed by `(source, code)` → `~/.cache/easyviz/<source>_<safe_code>.parquet`
    plus a small `.json` sidecar with the UTC snapshot timestamp.
  * Values older than `ttl_seconds` (default 24 h) are ignored.
  * The cache directory is honoured via the `EASYVIZ_CACHE_DIR`
    environment variable — set it to `/tmp` on ephemeral platforms,
    or point it at a persistent volume if you have one.

Read/write errors are non-fatal: the cache is a speedup, never a
correctness requirement, so a missing / corrupt file simply means
the caller will refetch.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_DEFAULT_DIR = Path.home() / ".cache" / "easyviz"


def _cache_dir() -> Path:
    override = os.environ.get("EASYVIZ_CACHE_DIR")
    d = Path(override) if override else _DEFAULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe(code: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in code)


def _paths(source: str, code: str) -> tuple[Path, Path]:
    base = _cache_dir() / f"{source}_{_safe(code)}"
    return base.with_suffix(".parquet"), base.with_suffix(".json")


def load(source: str, code: str, ttl_seconds: int = 86400) -> tuple[pd.DataFrame, datetime] | None:
    """Return (df, snapshot) if a fresh cached entry exists, else None."""
    data_path, meta_path = _paths(source, code)
    if not (data_path.exists() and meta_path.exists()):
        return None
    try:
        meta = json.loads(meta_path.read_text())
        snapshot = datetime.fromisoformat(meta["snapshot"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None

    age = (datetime.now(timezone.utc) - snapshot).total_seconds()
    if age > ttl_seconds:
        return None

    try:
        df = pd.read_parquet(data_path)
    except (OSError, ValueError):
        return None
    return df, snapshot


def save(source: str, code: str, df: pd.DataFrame, snapshot: datetime) -> None:
    """Write df + timestamp to disk; swallow IO errors silently."""
    data_path, meta_path = _paths(source, code)
    try:
        df.to_parquet(data_path, index=False)
        meta_path.write_text(json.dumps({"snapshot": snapshot.isoformat()}))
    except (OSError, ValueError, ImportError):
        # Parquet needs pyarrow/fastparquet; a missing engine should not
        # crash the app. The in-memory Streamlit cache still helps.
        return


def clear() -> int:
    """Delete every cached entry. Returns the number of files removed."""
    d = _cache_dir()
    n = 0
    for p in d.glob("*"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n
