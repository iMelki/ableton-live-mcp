from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from server import make_server  # noqa: E402

OUTPUT = ROOT / "docs" / "tools.md"


class _NullBridge:
    def request(self, method, params):
        raise NotImplementedError


def render() -> str:
    server = make_server(_NullBridge())
    lines = [
        "# MCP tool reference",
        "",
        "Generated from `src/server.py` by `scripts/generate_tool_docs.py`. Do not edit by hand — run:",
        "",
        "```sh",
        "python scripts/generate_tool_docs.py",
        "```",
        "",
        f"{len(server.tools)} tools.",
        "",
    ]
    for tool in server.tools.values():
        props = tool.input_schema.get("properties", {})
        required = set(tool.input_schema.get("required", []))
        lines.append(f"## `{tool.name}`")
        lines.append("")
        lines.append(tool.description)
        lines.append("")
        if props:
            lines.append("| Parameter | Type | Required | Description |")
            lines.append("|---|---|---|---|")
            for name, spec in props.items():
                ptype = spec.get("type") or ("one of" if "oneOf" in spec else "")
                desc = spec.get("description", "")
                lines.append(f"| `{name}` | {ptype} | {'yes' if name in required else ''} | {desc} |")
            lines.append("")
        else:
            lines.append("No parameters.")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
