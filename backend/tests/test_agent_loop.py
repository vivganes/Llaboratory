"""Unit tests for agent loop components (no real API calls)."""
import json
import pytest

from app.services.tool_executor import execute_tool, validate_args, execute_dynamic


# ── validate_args ────────────────────────────────────────────────────────────

def test_validate_args_valid():
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    errors = validate_args(schema, {"query": "hello"})
    assert errors == []


def test_validate_args_missing_required():
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    errors = validate_args(schema, {})
    assert len(errors) == 1
    assert "query" in errors[0]


def test_validate_args_wrong_type():
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
    errors = validate_args(schema, {"n": "not-an-int"})
    assert len(errors) == 1


def test_validate_args_empty_schema():
    errors = validate_args({"type": "object", "properties": {}}, {"anything": True})
    assert errors == []


# ── execute_tool: static ─────────────────────────────────────────────────────

def test_static_tool_returns_dict():
    result, err = execute_tool(
        "static", '{"answer": 42}', None, 1, {}, {}
    )
    assert err is None
    assert result == {"answer": 42}


def test_static_tool_invalid_json_fallback():
    result, err = execute_tool("static", "plain text", None, 1, {}, {})
    assert err is None
    assert result == {"result": "plain text"}


# ── execute_tool: dynamic ────────────────────────────────────────────────────

def test_dynamic_tool_basic():
    code = "def respond(args, context):\n    return {'echo': args.get('msg')}"
    result, err = execute_tool("dynamic", "{}", code, 1, {"msg": "hi"}, {})
    assert err is None
    assert result == {"echo": "hi"}


def test_dynamic_tool_stateful():
    code = "def respond(args, context):\n    context['n'] = context.get('n', 0) + 1\n    return {'count': context['n']}"
    ctx = {}
    result1, _ = execute_tool("dynamic", "{}", code, 1, {}, ctx)
    result2, _ = execute_tool("dynamic", "{}", code, 1, {}, ctx)
    assert result1 == {"count": 1}
    assert result2 == {"count": 2}


def test_dynamic_tool_unapproved_blocked():
    code = "def respond(args, context): return {}"
    result, err = execute_tool("dynamic", "{}", code, 0, {}, {})
    assert err is not None
    assert "approval" in err.lower()


def test_dynamic_tool_no_code():
    result, err = execute_tool("dynamic", "{}", None, 1, {}, {})
    assert err is not None


def test_dynamic_tool_runtime_error():
    code = "def respond(args, context): raise ValueError('oops')"
    result, err = execute_tool("dynamic", "{}", code, 1, {}, {})
    assert err is not None
    assert "oops" in err


def test_dynamic_tool_compile_error():
    code = "def respond(args context):\n    pass"  # syntax error
    result, err = execute_tool("dynamic", "{}", code, 1, {}, {})
    assert err is not None


# ── execute_tool: unknown mode ───────────────────────────────────────────────

def test_unknown_response_mode():
    result, err = execute_tool("banana", "{}", None, 1, {}, {})
    assert err is not None
    assert "banana" in err
