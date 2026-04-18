"""
Tests for the URL-state helpers.

We don't spin up Streamlit here — instead we monkeypatch
`src.urlstate.st.query_params` with a tiny dict-shaped stand-in that
mimics the two operations the module actually uses: item access
(`qp[k]`, `qp.get(k, default)`) and item deletion (`del qp[k]`).
"""

from __future__ import annotations

import pytest

import src.urlstate as us


class _FakeQP:
    """Minimal duck-type for st.query_params."""

    def __init__(self, initial: dict[str, str] | None = None):
        self._d = dict(initial or {})

    def get(self, k, default=""):
        return self._d.get(k, default)

    def __getitem__(self, k):
        return self._d[k]

    def __setitem__(self, k, v):
        self._d[k] = v

    def __delitem__(self, k):
        del self._d[k]

    def __contains__(self, k):
        return k in self._d


@pytest.fixture
def qp(monkeypatch):
    fake = _FakeQP()
    monkeypatch.setattr(us.st, "query_params", fake)
    return fake


def test_is_embed_detects_flag(qp):
    assert us.is_embed() is False
    qp["embed"] = "1"
    assert us.is_embed() is True
    qp["embed"] = "true"
    assert us.is_embed() is True
    qp["embed"] = "0"
    assert us.is_embed() is False


def test_list_round_trip(qp):
    us.set_list("countries", ["France", "Germany", "Italy"])
    assert qp["countries"] == "France,Germany,Italy"
    assert us.get_list("countries") == ["France", "Germany", "Italy"]


def test_empty_list_clears_key(qp):
    qp["countries"] = "seed"
    us.set_list("countries", [])
    assert "countries" not in qp
    assert us.get_list("countries") == []


def test_int_pair_round_trip(qp):
    us.set_int_pair("years", (2000, 2024))
    assert qp["years"] == "2000-2024"
    assert us.get_int_pair("years") == (2000, 2024)


def test_int_pair_malformed_returns_none(qp):
    qp["years"] = "abc"
    assert us.get_int_pair("years") is None
    qp["years"] = "2020"
    assert us.get_int_pair("years") is None


def test_bool_helpers(qp):
    assert us.get_bool("log") is False
    us.set_bool("log", True)
    assert qp["log"] == "1"
    assert us.get_bool("log") is True
    us.set_bool("log", False)
    assert "log" not in qp


def test_set_param_clears_on_empty(qp):
    qp["x"] = "prev"
    us.set_param("x", "")
    assert "x" not in qp
    us.set_param("x", None)
    assert "x" not in qp
    us.set_param("x", "hello")
    assert qp["x"] == "hello"
