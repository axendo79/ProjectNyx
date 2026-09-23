"""Ordinary writer tests never depend on the machine's wall clock."""

import pytest

from nyx import writer


@pytest.fixture(autouse=True)
def fixed_writer_clock(monkeypatch):
    monkeypatch.setattr(writer, "clock_now", lambda: "2026-07-13T12:00:00Z")
