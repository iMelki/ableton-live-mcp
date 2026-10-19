"""Run the documented Ableton recipes against a *live* Ableton Live set and report what actually works.

Usage (Live running with the Ableton_Live_MCP control surface selected):

    python src/recipe_check.py --yes

This creates throwaway tracks named "MCP Verify ..." in the open Live Set and
deletes them at the end. Use a blank/disposable set; back up anything you care
about first (the MCP can edit your set directly).

Each step prints pass/fail/skip plus the raw details Live returned, so the
answer to "does this recipe really work on my Live version?" is observed, not
assumed.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bridge import AbletonBridgeClient

TRACK_PREFIX = "MCP Verify"

CREATE_TRACKS_CODE = """
names = {names!r}
created = []
for name in names:
    song.create_midi_track(len(song.tracks))
    track = song.tracks[len(song.tracks) - 1]
    track.name = name
    created.append({{"index": len(song.tracks) - 1, "name": name}})
result = created
"""

CREATE_CLIP_CODE = """
song.tracks[{index}].clip_slots[0].create_clip({length})
result = {{"has_clip": bool(song.tracks[{index}].clip_slots[0].has_clip)}}
"""

ROUTING_CODE = """
track = song.tracks[{index}]
def names(items):
    return [getattr(item, "display_name", str(item)) for item in items]
info = {{"output_types": names(getattr(track, "available_output_routing_types", []))}}
info["current_output_type"] = getattr(getattr(track, "output_routing_type", None), "display_name", None)
result = info
"""

COMPRESSOR_ROUTING_CODE = """
track = song.tracks[{index}]
device = track.devices[{device_index}]
def names(items):
    return [getattr(item, "display_name", str(item)) for item in items]
result = {{
    "device": device.name,
    "available_input_routing_types": names(getattr(device, "available_input_routing_types", [])),
    "has_input_routing_type": hasattr(device, "input_routing_type"),
}}
"""

CLEANUP_CODE = """
removed = 0
for i in range(len(song.tracks) - 1, -1, -1):
    if song.tracks[i].name.startswith({prefix!r}):
        song.delete_track(i)
        removed += 1
result = {{"removed": removed, "tracks_remaining": len(song.tracks)}}
"""


def _step(name: str, status: str, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail}


def _entries(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict):
        for key in ("parameters", "items", "notes", "results"):
            if isinstance(result.get(key), list):
                return [item for item in result[key] if isinstance(item, dict)]
        return []
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _names(result: Any) -> list[str]:
    return [str(item.get("name")) for item in _entries(result) if item.get("name") is not None]


def _create_tracks(client: Any, names: list[str]) -> list[int]:
    created = client.request("exec", {"code": CREATE_TRACKS_CODE.format(names=names)})
    return [int(item["index"]) for item in created]


def check_ping(client: Any) -> dict[str, Any]:
    result = client.request("ping", {})
    return _step("ping", "pass", result)


def check_sidechain(client: Any) -> dict[str, Any]:
    kick, bass = _create_tracks(client, [f"{TRACK_PREFIX} Kick", f"{TRACK_PREFIX} Bass"])
    inserted = client.request("track_insert_device", {"ref": {"path": f"live_set tracks {bass}"}, "device_name": "Compressor"})
    if not inserted.get("inserted"):
        return _step("sidechain", "fail", {"reason": "Compressor was not inserted", "result": inserted})
    params = client.request("device_parameters", {"ref": {"path": f"live_set tracks {bass} devices 0"}, "query": "S/C", "limit": 20})
    sidechain_params = _entries(params)
    detail: dict[str, Any] = {"sidechain_parameter_names": _names(params), "kick_track": kick, "bass_track": bass}
    toggle = next((p for p in sidechain_params if str(p.get("name", "")).strip().lower() == "s/c on"), None)
    if toggle is None or toggle.get("id") is None:
        return _step("sidechain", "fail", {**detail, "reason": "no 'S/C On' parameter found; recipe parameter names need updating"})
    client.request("parameter_set", {"ref": {"id": toggle["id"]}, "value": 1})
    detail["sidechain_enabled"] = True
    routing = client.request("exec", {"code": COMPRESSOR_ROUTING_CODE.format(index=bass, device_index=0)})
    detail["routing"] = routing
    wanted = f"{TRACK_PREFIX} Kick"
    if any(wanted in str(name) for name in routing.get("available_input_routing_types", [])):
        detail["kick_selectable_as_sidechain_source"] = True
        return _step("sidechain", "pass", detail)
    return _step("sidechain", "partial", {**detail, "note": "S/C toggled, but the source track was not offered as a routing type; routing step needs a different LOM path on this Live version"})


def check_chord_track(client: Any) -> dict[str, Any]:
    melody, chords = _create_tracks(client, [f"{TRACK_PREFIX} Melody", f"{TRACK_PREFIX} Chords"])
    for index in (melody, chords):
        client.request("exec", {"code": CREATE_CLIP_CODE.format(index=index, length=4.0)})
    melody_ref = {"path": f"live_set tracks {melody} clip_slots 0 clip"}
    chord_ref = {"path": f"live_set tracks {chords} clip_slots 0 clip"}
    melody_notes = [{"pitch": p, "start_time": float(i), "duration": 1.0, "velocity": 90} for i, p in enumerate([64, 67, 65, 62])]
    client.request("clip_add_notes", {"ref": melody_ref, "notes": melody_notes, "clear": True})
    read_back = _entries(client.request("clip_notes", {"ref": melody_ref, "limit": 64}))
    if len(read_back) != len(melody_notes):
        return _step("chord_track", "fail", {"reason": "melody did not round-trip", "wrote": len(melody_notes), "read": len(read_back)})
    triads = {0: (60, 64, 67), 1: (60, 64, 67), 2: (53, 57, 60), 3: (55, 59, 62)}
    chord_notes = [{"pitch": p, "start_time": float(bar), "duration": 1.0, "velocity": 80} for bar, pitches in triads.items() for p in pitches]
    client.request("clip_add_notes", {"ref": chord_ref, "notes": chord_notes, "clear": True})
    chord_read = _entries(client.request("clip_notes", {"ref": chord_ref, "limit": 64}))
    status = "pass" if len(chord_read) == len(chord_notes) else "fail"
    return _step("chord_track", status, {"melody_notes": len(read_back), "chord_notes_written": len(chord_notes), "chord_notes_read": len(chord_read)})


def check_dj_crossfade(client: Any) -> dict[str, Any]:
    (track,) = _create_tracks(client, [f"{TRACK_PREFIX} DJ"])
    mixer = {"path": f"live_set tracks {track} mixer_device"}
    original = client.request("get", {"ref": mixer, "properties": ["crossfade_assign"]})
    observed: dict[str, Any] = {}
    for value in (0, 1, 2):
        client.request("set", {"ref": mixer, "property": "crossfade_assign", "value": value})
        readback = client.request("get", {"ref": mixer, "properties": ["crossfade_assign"]})
        observed[str(value)] = readback
    detail: dict[str, Any] = {"original": original, "after_set": observed}
    macro_probe = client.request("track_insert_device", {"ref": {"path": f"live_set tracks {track}"}, "device_name": "Audio Effect Rack"})
    detail["audio_effect_rack_inserted"] = bool(macro_probe.get("inserted"))
    if macro_probe.get("inserted"):
        params = client.request("device_parameters", {"ref": {"path": f"live_set tracks {track} devices 0"}, "query": "Macro", "limit": 20})
        detail["macro_parameter_names"] = _names(params)
    return _step("dj_crossfade_and_macros", "pass" if observed else "fail", detail)


def check_external_instrument_routing(client: Any) -> dict[str, Any]:
    (track,) = _create_tracks(client, [f"{TRACK_PREFIX} External"])
    routing = client.request("exec", {"code": ROUTING_CODE.format(index=track)})
    inserted = client.request("track_insert_device", {"ref": {"path": f"live_set tracks {track}"}, "device_name": "External Instrument"})
    detail: dict[str, Any] = {"routing": routing, "external_instrument_inserted": bool(inserted.get("inserted"))}
    if inserted.get("inserted"):
        params = client.request("device_parameters", {"ref": {"path": f"live_set tracks {track} devices 0"}, "limit": 30})
        detail["external_instrument_parameter_names"] = _names(params)
    return _step("external_instrument_routing", "pass" if routing.get("output_types") else "fail", detail)


def check_videosync_probe(client: Any) -> dict[str, Any]:
    result = client.request("browser_search", {"query": "Videosync", "limit": 5})
    matches = _entries(result)
    if not matches:
        return _step("videosync_probe", "skip", {"reason": "no browser item matching 'Videosync' (not installed, or not indexed)"})
    return _step("videosync_probe", "pass", {"matches": [item.get("name") for item in matches]})


CHECKS = [
    check_ping,
    check_sidechain,
    check_chord_track,
    check_dj_crossfade,
    check_external_instrument_routing,
    check_videosync_probe,
]


def run_recipe_checks(client: Any) -> tuple[int, dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    try:
        for check in CHECKS:
            try:
                steps.append(check(client))
            except Exception as exc:  # report and continue; one failing recipe shouldn't hide the others
                steps.append(_step(check.__name__.removeprefix("check_"), "fail", {"error": str(exc)}))
    finally:
        try:
            cleanup = client.request("exec", {"code": CLEANUP_CODE.format(prefix=TRACK_PREFIX)})
        except Exception as exc:
            cleanup = {"error": str(exc), "note": f"delete any tracks named '{TRACK_PREFIX} ...' manually"}
    failed = [step["name"] for step in steps if step["status"] == "fail"]
    summary = {"ok": not failed, "failed": failed, "steps": steps, "cleanup": cleanup}
    return (0 if not failed else 1), summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the documented recipes against a running Ableton Live set.")
    parser.add_argument("--yes", action="store_true", help="Confirm that creating/deleting throwaway 'MCP Verify' tracks in the open Live Set is OK.")
    args = parser.parse_args(argv)
    if not args.yes:
        print("This creates and deletes throwaway tracks in the open Live Set. Use a disposable set, then re-run with --yes.", file=sys.stderr)
        return 2
    code, summary = run_recipe_checks(AbletonBridgeClient())
    print(json.dumps(summary, indent=2, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
