"""Tests for MCP server JSON-RPC handling."""

from __future__ import annotations

import json

from lostdog_mcp.server import handle_request
from lostdog_mcp.storage.db import get_engine, reset_engine


def setup_module():
    reset_engine()
    get_engine("sqlite:///:memory:")


def teardown_module():
    reset_engine()


def test_initialize():
    resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["serverInfo"]["name"] == "lostdog-deepsearch-mcp"


def test_tools_list():
    resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "case_create" in names
    assert "candidate_list" in names
    assert "case_export_bundle" in names


def test_case_create_via_rpc():
    resp = handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "case_create",
            "arguments": {
                "title": "Missing corgi",
                "last_seen_at": "2025-06-26T18:00:00",
                "last_seen_location": "Conroe TX",
            },
        },
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "case_id" in content
    assert content["title"] == "Missing corgi"


def test_unknown_tool():
    resp = handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    assert resp["error"]["code"] == -32601


def test_unknown_method():
    resp = handle_request({"jsonrpc": "2.0", "id": 5, "method": "foo/bar", "params": {}})
    assert resp["error"]["code"] == -32601
