"""Tests for evidence service."""

from __future__ import annotations

import json
from pathlib import Path

from lostdog_mcp.services.evidence_service import check_duplicate_evidence, list_evidence


def test_check_duplicate_no_evidence(tmp_path):
    assert check_duplicate_evidence(str(tmp_path), "abc123") is None


def test_check_duplicate_finds_match(tmp_path):
    meta = {"content_hash": "abc123", "html_path": "/some/path.html"}
    (tmp_path / "test.meta.json").write_text(json.dumps(meta))
    result = check_duplicate_evidence(str(tmp_path), "abc123")
    assert result == "/some/path.html"


def test_check_duplicate_no_match(tmp_path):
    meta = {"content_hash": "other_hash", "html_path": "/some/path.html"}
    (tmp_path / "test.meta.json").write_text(json.dumps(meta))
    assert check_duplicate_evidence(str(tmp_path), "abc123") is None


def test_list_evidence_empty(tmp_path):
    result = list_evidence(str(tmp_path))
    assert result == []


def test_list_evidence_with_files(tmp_path):
    for i in range(3):
        meta = {"url": f"https://example.com/{i}", "content_hash": f"hash{i}"}
        (tmp_path / f"evidence_{i}.meta.json").write_text(json.dumps(meta))
    result = list_evidence(str(tmp_path))
    assert len(result) == 3
