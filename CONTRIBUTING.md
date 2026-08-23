# Contributing

## Dev setup

```sh
python -m pip install -e ".[dev]"
```

This installs the package in editable mode plus `pytest`, `ruff`, and the
visual-capture/audio dependencies used by some tests (`Pillow`, `pydub`,
platform-conditional `pyobjc`/`windows-capture` packages).

## Running tests

```sh
python -m pytest
```

The test suite runs almost entirely against fake/in-memory bridges
(`FakeBridge` in `tests/test_mcp_server.py`, the fake Live object model in
`tests/test_remote_bridge_fake_live.py`) — no Ableton Live installation is
required for most of it.

**Known gap on non-macOS/Windows runners:** 16 tests under `test_validate_*`
exercise `ableton-live-mcp-validate`'s M4L-host check, which is gated to
macOS/Windows (`agent_m4l_host_status`/`ableton_paths`) and fail on Linux
independent of any code change. CI deselects them explicitly (see
`.github/workflows/ci.yml`) rather than silently passing or silently
failing — this is pre-existing, not something a given PR needs to fix.

## Linting

```sh
ruff check .
ruff format --check .
```

Only pyflakes rules (`F`) are enabled for `ruff check` — real bugs (unused
imports, undefined names), not style; import-sorting/pyupgrade rules aren't
enabled. `ruff format` handles style and the codebase is kept clean against
it — run `ruff format .` before committing if it flags anything.

## Making changes to the MCP tool surface (`src/server.py`)

- Every tool needs a non-empty `description`. A strict schema (built with
  `schema(...)`) needs `additionalProperties: False` and every real
  accepted property declared — `schema({})` means "accepts zero
  arguments," not "accepts anything." For tools whose arguments are
  genuinely too flexible to enumerate, use `loose_schema()` instead (see
  its docstring in `server.py`) rather than declaring a strict schema you
  won't keep in sync.
- `mcp_stdio.py` enforces at registration time that every schema is a
  well-formed JSON Schema object; `tests/test_schema_consistency.py`
  separately checks that every strict-schema tool declares every `params`
  key its corresponding `_rpc_*` handler in `Ableton_Live_MCP/bridge.py`
  actually reads — cross-check new/changed strict-schema tools against
  their handler if you're not relying on that test to catch drift for you.
- The full `tools/list` JSON payload is budget-capped
  (`test_tool_list_stays_compact` in `tests/test_mcp_server.py`) to keep
  the tool list token-cheap for the calling agent. If your change pushes
  the payload over the current budget, that's a real tradeoff to make
  deliberately (raise the budget with a comment explaining why), not paper
  over.
- `docs/tools.md` is generated, not hand-written. Run
  `python scripts/generate_tool_docs.py` after changing any tool's
  schema/description; `test_generated_tool_docs_are_up_to_date` fails CI
  if you forget.
- Keep tool/parameter descriptions terse — this project is explicitly
  optimized for low end-to-end latency and low token usage (see README and
  `AGENTS.md`'s compact `ABLETON_MCP_INSTRUCTIONS`).

## Building the Max for Live device

```sh
.venv/bin/python scripts/build_agent_audio_tap.py --install
```

Requires an actual Ableton Live + Max for Live install to test the built
`.amxd` device; the build script itself is covered by
`tests/test_agent_audio_tap_build.py` without one. `scripts/build_agent_m4l_device.py`
and `tests/test_agent_m4l_build.py` cover the newer `AgentM4L` build path
similarly.

## Testing against real Ableton Live

Most of the codebase can be developed and tested without Ableton Live open
(see "Running tests" above). Changes to `Ableton_Live_MCP/bridge.py`'s
actual Live Object Model calls, transport control, visual capture, or the
Max for Live devices can only be fully verified against a running Live
instance — call this out explicitly in your PR description if you were not
able to test against real Ableton, since this project edits users' Live
Sets directly and a broken change can corrupt someone's work (see the
backup warning in README.md). `AGENTS.md` has detailed guidance on bridge
reliability, validation, and recovery scenarios worth reading before making
changes in this area.

## Pull requests

- Run `pytest` and `ruff check . && ruff format --check .` before opening a
  PR.
- Fetch and check `origin/main`'s current state before pushing, especially
  for a long-running branch — this repo moves fast and a stale local base
  can lead to redundant or conflicting work.
- Reference the issue you're closing (`Closes #N`) where applicable.
