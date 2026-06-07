"""Executes fake tool calls based on their response mode."""
from __future__ import annotations
import json
import jsonschema


class ToolValidationError(Exception):
    pass


def validate_args(parameter_schema: dict, args: dict) -> list[str]:
    """Returns list of validation error messages, empty if valid."""
    try:
        jsonschema.validate(instance=args, schema=parameter_schema)
        return []
    except jsonschema.ValidationError as e:
        return [e.message]
    except jsonschema.SchemaError as e:
        return [f"Schema error: {e.message}"]


def execute_static(static_response: dict | str) -> dict:
    if isinstance(static_response, str):
        try:
            return json.loads(static_response)
        except json.JSONDecodeError:
            return {"result": static_response}
    return static_response


def execute_dynamic(dynamic_code: str, args: dict, session_context: dict) -> dict:
    """
    Executes user-written Python function `def respond(args, context) -> response`.
    context is a per-session mutable dict for stateful tools.

    WARNING: executes arbitrary code without sandboxing.
    Only for locally-authored tools (see README security disclaimer).
    """
    namespace: dict = {}
    try:
        exec(dynamic_code, namespace)  # noqa: S102
    except Exception as e:
        raise ToolValidationError(f"Dynamic code compile error: {e}") from e

    respond_fn = namespace.get("respond")
    if not callable(respond_fn):
        raise ToolValidationError("Dynamic code must define `def respond(args, context)`")

    try:
        result = respond_fn(args, session_context)
    except Exception as e:
        raise ToolValidationError(f"Dynamic code runtime error: {e}") from e

    if isinstance(result, (dict, list, str, int, float, bool, type(None))):
        return result if isinstance(result, dict) else {"result": result}
    return {"result": str(result)}


def execute_tool(
    response_mode: str,
    static_response_raw: str,
    dynamic_code: str | None,
    dynamic_approved: int,
    args: dict,
    session_context: dict,
) -> tuple[dict, str | None]:
    """
    Returns (result_dict, error_message).
    error_message is None on success.
    """
    if response_mode == "static":
        try:
            static_response = json.loads(static_response_raw) if isinstance(static_response_raw, str) else static_response_raw
        except json.JSONDecodeError:
            static_response = {"result": static_response_raw}
        return execute_static(static_response), None

    if response_mode == "dynamic":
        if not dynamic_code:
            return {}, "No dynamic code defined for this tool"
        if not dynamic_approved:
            return {}, "Dynamic tool requires approval before execution (imported tool)"
        try:
            return execute_dynamic(dynamic_code, args, session_context), None
        except ToolValidationError as e:
            return {}, str(e)

    if response_mode == "manual":
        # Manual mode is not yet implemented in MVP; return a placeholder
        return {"_manual": True, "message": "Manual tool — response pending"}, None

    return {}, f"Unknown response mode: {response_mode}"
