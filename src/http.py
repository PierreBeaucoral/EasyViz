"""
Shared HTTP session for EasyViz.

A single `requests.Session` with connection pooling is reused across
`fetcher`, `metadata`, and `geo`. Pooling matters because:

  * The World Bank API is paginated — a typical indicator fetch is 2–5
    sequential calls to the same host. Reusing the TCP + TLS connection
    cuts per-page latency by ~80 ms in our profiling.
  * The compare page fires 2–6 parallel fetches; without pooling each
    worker opens its own connection and the cold start dominates.
  * geoBoundaries serves a metadata JSON then redirects to a GitHub
    asset; the redirect benefits from connection reuse as well.

The session is importable as `src.http.session` so tests can
monkeypatch `session.get` directly.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter

_USER_AGENT = "EasyViz/0.2 (+https://github.com/PierreBeaucoral/EasyViz)"


def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _USER_AGENT})
    adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=0)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


session: requests.Session = _build_session()
