from __future__ import annotations

import pytest

import recipe_check


class ScriptedLive:
    """Minimal stand-in for the bridge client that behaves like a cooperative Live."""

    def __init__(self, fail_on: str | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.tracks: list[str] = []
        self.clip_notes: dict[str, list] = {}
        self.fail_on = fail_on

    def request(self, method, params):
        self.calls.append((method, params))
        if self.fail_on == method:
            raise RuntimeError("boom from %s" % method)
        code = params.get("code", "")
        if method == "exec" and "create_midi_track" in code:
            names = eval(code.split("names = ", 1)[1].split("\n", 1)[0])
            created = []
            for name in names:
                self.tracks.append(name)
                created.append({"index": len(self.tracks) - 1, "name": name})
            return created
        if method == "exec" and "create_clip" in code:
            return {"has_clip": True}
        if method == "exec" and "available_input_routing_types" in code:
            return {"device": "Compressor", "available_input_routing_types": ["Ext. In", "MCP Verify Kick"], "has_input_routing_type": True}
        if method == "exec" and "available_output_routing_types" in code:
            return {"output_types": ["Master", "Ext. Out"], "current_output_type": "Master"}
        if method == "exec" and "delete_track" in code:
            removed = len(self.tracks)
            self.tracks = []
            return {"removed": removed, "tracks_remaining": 0}
        if method == "track_insert_device":
            return {"inserted": True, "device_name": params["device_name"]}
        if method == "device_parameters":
            query = params.get("query")
            if query == "S/C":
                return {"parameters": [{"id": 5, "name": "S/C On"}, {"id": 6, "name": "S/C Gain"}]}
            if query == "Macro":
                return {"parameters": [{"id": 9, "name": "Macro 1"}]}
            return {"parameters": [{"id": 1, "name": "Device On"}]}
        if method == "clip_add_notes":
            self.clip_notes[params["ref"]["path"]] = list(params["notes"])
            return {"ok": True}
        if method == "clip_notes":
            return {"notes": self.clip_notes.get(params["ref"]["path"], [])}
        if method == "get":
            return {"properties": {"crossfade_assign": 1}}
        if method == "browser_search":
            return {"results": []}
        return {"ok": True}


def test_main_requires_explicit_confirmation(capsys):
    assert recipe_check.main([]) == 2
    assert "--yes" in capsys.readouterr().err


def test_all_recipes_pass_against_a_cooperative_live_and_clean_up():
    live = ScriptedLive()
    code, summary = recipe_check.run_recipe_checks(live)

    statuses = {step["name"]: step["status"] for step in summary["steps"]}
    assert code == 0
    assert statuses["sidechain"] == "pass"
    assert statuses["chord_track"] == "pass"
    assert statuses["dj_crossfade_and_macros"] == "pass"
    assert statuses["external_instrument_routing"] == "pass"
    assert statuses["videosync_probe"] == "skip"
    assert summary["cleanup"]["tracks_remaining"] == 0
    assert live.tracks == []
    # cleanup is the very last bridge call
    last_method, last_params = live.calls[-1]
    assert last_method == "exec" and "delete_track" in last_params["code"]


def test_dj_check_probes_every_crossfade_value_and_restores_nothing_unobserved():
    live = ScriptedLive()
    _, summary = recipe_check.run_recipe_checks(live)
    dj = next(step for step in summary["steps"] if step["name"] == "dj_crossfade_and_macros")
    set_values = [params["value"] for method, params in live.calls if method == "set" and params["property"] == "crossfade_assign"]
    assert set_values == [0, 1, 2]
    assert set(dj["detail"]["after_set"]) == {"0", "1", "2"}
    assert dj["detail"]["macro_parameter_names"] == ["Macro 1"]


def test_a_failing_step_is_reported_and_cleanup_still_runs():
    live = ScriptedLive(fail_on="clip_add_notes")
    code, summary = recipe_check.run_recipe_checks(live)

    assert code == 1
    assert "chord_track" in summary["failed"]
    assert summary["cleanup"]["tracks_remaining"] == 0
    assert live.tracks == []


def test_sidechain_fails_clearly_when_parameter_names_differ():
    live = ScriptedLive()
    original = live.request

    def renamed(method, params):
        if method == "device_parameters" and params.get("query") == "S/C":
            live.calls.append((method, params))
            return {"parameters": [{"id": 5, "name": "Sidechain Toggle"}]}
        return original(method, params)

    live.request = renamed
    _, summary = recipe_check.run_recipe_checks(live)
    sidechain = next(step for step in summary["steps"] if step["name"] == "sidechain")
    assert sidechain["status"] == "fail"
    assert "S/C On" in sidechain["detail"]["reason"]


@pytest.mark.parametrize("payload", [{"parameters": [{"name": "A"}]}, [{"name": "A"}], {"nothing": 1}, None])
def test_entry_helpers_tolerate_varied_response_shapes(payload):
    assert isinstance(recipe_check._names(payload), list)
