# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project does not
yet follow semantic version tags.

## [0.1.2] - 2026-08-23

### Added
- CI workflow (`.github/workflows/ci.yml`): `pytest` on Linux (Python 3.10,
  3.12) and macOS, plus `ruff check` and `ruff format --check`, on every
  push/PR. Nothing ran the test suite automatically before this.
- `ruff` lint config (pyflakes + import-sorting rules) and a repo-wide
  `ruff format` pass — the codebase is now clean against both. Pyupgrade
  (`UP`) rules were evaluated and deliberately not enabled: most of its
  findings want to rewrite the codebase's consistent, intentional
  `%`-style string formatting to f-strings, a large unrelated stylistic
  diff rather than a mechanical fix.
- `live_prep_vocal_sample` MCP tool (`src/vocal_prep.py`): trims leading/
  trailing silence (`pydub`) and transcribes (`faster-whisper`, optional
  `vocals` extra) a vocal sample file. Implements one of README's "Ideas"
  bullets.
- `docs/roadmap-ideas.md`: feasibility research (Live Object Model APIs,
  prior art, implementation sketches) for all of README's "Ideas" bullets.
- Regression tests: every MCP tool has a non-empty description; the
  generated tool reference doc (`docs/tools.md`, via
  `scripts/generate_tool_docs.py`) stays in sync with the schema; a static
  (AST-based) check that every strict-schema tool declares every `params`
  key its bridge RPC handler actually reads (complementary to
  `mcp_stdio.py`'s existing registration-time schema-shape guard).
- `CONTRIBUTING.md`, and dev-workflow notes in `AGENTS.md` (schema vs.
  `loose_schema()` guidance, the `tools/list` compactness budget, the
  known Linux-only `test_validate_*` gap and its macOS CI coverage,
  `faster-whisper` model download/caching behavior, mypy survey findings).

### Fixed
- Two dead unused imports (`ruff check`): a redundant `Quartz` re-import in
  `visual_capture.py`'s `capture_macos_window_quartz` already covered by
  `write_cgimage_png`'s own import, and an unused `pathlib.Path` import in
  `tests/test_ableton_paths.py`.

## History

This project doesn't tag releases; below is a high-level summary of the
codebase's evolution to date, for context rather than a strict per-commit
log.

- Initial build (early May): core MCP server bridging to Ableton Live's
  Object Model via a Remote Script + JSON-RPC socket bridge, with
  general-purpose (`live_get`/`live_set`/`live_call`, `live_eval`/
  `live_exec`, `live_batch`) and task-specific tools (clip note editing,
  clip envelopes, warp markers, device parameter inspection, browser
  search/load/preview), argument validation against JSON Schema, and
  latency/token-usage optimization work (compact response shaping,
  buffered/reused bridge sockets, `find_similar_sounds` reading Live 12's
  local sound-analysis database directly).
- `AgentAudioTap` Max for Live device + `live_agent_audio_tap`/
  `live_agent_audio_tap_setup` tools: an audio capture + analysis feedback
  loop at any point in a track's signal chain.
- `live_transport` tool for playback/seek control.
- A regression where three tools (`live_agent_audio_tap`,
  `live_agent_audio_tap_setup`, `live_transport`) shipped with a bare `{}`
  `inputSchema`, violating the MCP spec and making strict clients reject the
  entire `tools/list` response, was fixed (#4) — then, since a schema with
  `additionalProperties: false` and empty `properties` accepts *only* empty
  arguments, that fix briefly meant the same three tools rejected every
  real argument until `loose_schema()` was introduced for tools that
  genuinely need flexible arguments (#8).
- Significant expansion: an `AgentM4L` system for building/loading Max for
  Live devices from a spec (`agent_m4l.py`, `live_agent_m4l_device`/
  `live_agent_m4l_cleanup`), visual capture tooling
  (`visual_capture.py`, `live_visual_capture`, `live_max_console_capture`)
  for an agent to inspect Live/M4L UI state directly, platform-path
  handling extracted into its own module (`ableton_paths.py`), and
  `live_load_device`/`live_bridge_status`/`live_batch` additions — 37 tools
  as of the last commit before this changelog started.
