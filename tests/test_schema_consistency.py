from __future__ import annotations

import ast
from pathlib import Path

from server import make_server

BRIDGE_SOURCE = Path(__file__).resolve().parents[1] / "Ableton_Live_MCP" / "bridge.py"


class FakeBridge:
    def request(self, method, params):
        return {"method": method, "params": params}


def _bridge_method_for(tool):
    """Recover the bridge RPC method name a tool's handler forwards to.

    server.py builds each forwarding handler via `forward(method)`, a closure
    over `method`. Tools that don't forward to the bridge (e.g.
    find_similar_sounds, live_prep_vocal_sample, live_visual_capture) have no
    such free variable.
    """
    handler = tool.handler
    freevars = handler.__code__.co_freevars
    if "method" not in freevars or handler.__closure__ is None:
        return None
    index = freevars.index("method")
    return handler.__closure__[index].cell_contents


def _rpc_handler_defs(source: str) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(source)
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_rpc_"):
            defs[node.name[len("_rpc_") :]] = node
    return defs


def _params_keys_read(func: ast.FunctionDef) -> set[str]:
    """Statically extract every literal key read off the `params` argument.

    Covers `params.get("key", ...)` and `params["key"]`. This is a best-effort
    static scan, not a full data-flow analysis: it will miss keys read via
    aliases (`p = params; p.get(...)`) or built dynamically, and that's an
    accepted limitation of a lightweight regression guard, not something this
    test tries to solve generally.
    """
    keys: set[str] = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "params"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "params":
            slice_node = node.slice
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                keys.add(slice_node.value)
    return keys


def test_strict_schema_tools_declare_every_key_their_handler_reads():
    """Guards against a specific bug class: a tool with a strict
    (additionalProperties: false) schema whose handler reads a `params` key
    the schema never declares, which makes every real call using that key
    fail with "arguments has unknown fields". A schema declaring MORE keys
    than the handler reads is fine (e.g. forward-compatible fields) — only
    the handler-reads-but-schema-doesn't-declare direction is a bug.

    Only schemas with additionalProperties: False (built via server.py's
    schema() helper, as opposed to loose_schema()) are in scope: that's the
    only shape where an undeclared key can cause a valid call to be rejected
    at all. This is a static, complementary check to mcp_stdio.py's
    registration-time guard that every schema is a well-formed JSON Schema
    object -- that guard catches malformed schemas, this one catches
    schemas that are well-formed but incomplete relative to what the
    handler actually reads.
    """
    server = make_server(FakeBridge())
    rpc_defs = _rpc_handler_defs(BRIDGE_SOURCE.read_text(encoding="utf-8"))

    checked = 0
    problems = []
    for tool in server.tools.values():
        method = _bridge_method_for(tool)
        if method is None or method not in rpc_defs:
            continue
        if tool.input_schema.get("additionalProperties") is not False:
            continue
        declared = set(tool.input_schema.get("properties", {}).keys())
        read = _params_keys_read(rpc_defs[method])
        undeclared = read - declared
        checked += 1
        if undeclared:
            problems.append("%s (-> %s): handler reads undeclared params %s" % (tool.name, method, sorted(undeclared)))

    # Guard the guard: if closure/AST detection silently breaks (e.g. server.py
    # stops using forward()), this test should fail loudly instead of quietly
    # checking zero tools and always passing.
    assert checked >= 15, "expected to check most forwarding tools, only checked %d" % checked
    assert problems == [], "\n".join(problems)


def test_bridge_method_detection_resolves_a_known_tool():
    server = make_server(FakeBridge())
    assert _bridge_method_for(server.tools["live_ping"]) == "ping"
    assert _bridge_method_for(server.tools["find_similar_sounds"]) is None
