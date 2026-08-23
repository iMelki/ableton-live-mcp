# MCP tool reference

Generated from `src/server.py` by `scripts/generate_tool_docs.py`. Do not edit by hand — run:

```sh
python scripts/generate_tool_docs.py
```

38 tools.

## `live_ping`

Bridge health.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `timeout` | number |  |  |

## `live_bridge_status`

Socket-thread status; no Live API/main-thread scheduling.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `timeout` | number |  |  |

## `live_get`

Resolve object; read selected properties/children.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `properties` | array |  |  |
| `children` | one of |  |  |
| `child_limit` | integer |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_set_summary`

Compact set summary.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `track_limit` | integer |  |  |
| `clip_slot_limit` | integer |  |  |
| `device_limit` | integer |  |  |
| `arrangement_clip_limit` | integer |  |  |
| `track_query` | string |  |  |
| `include_return_tracks` | boolean |  |  |
| `include_master_track` | boolean |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_set`

Set a writable Live object property.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `property` | string | yes |  |
| `value` |  | yes |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_call`

Call one Live object method.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `method` | string | yes |  |
| `args` | array |  |  |
| `kwargs` | object |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_children`

List child objects from a collection.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `child` | string | yes |  |
| `limit` | integer |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_device_parameters`

Compact Device parameter metadata.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `query` | string |  |  |
| `limit` | integer |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_parameter_set`

Set DeviceParameter value.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `value` | number | yes |  |
| `coerce` | boolean |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_notes`

List MIDI notes from a clip compactly.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `limit` | integer |  |  |
| `start_time` | number |  |  |
| `end_time` | number |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_clip_update_notes`

Update existing MIDI notes by note_id.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `updates` | array | yes |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_add_notes`

Add notes; create a MIDI clip.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `notes` | array | yes |  |
| `clear` | boolean |  |  |
| `create_clip_length` | number |  |  |
| `clip_name` | string |  |  |
| `fire` | boolean |  |  |
| `replace_existing_clip` | boolean |  |  |
| `allow_legacy_note_api` | boolean |  |  |
| `clear_range` | object |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_duplicate_to_arrangement`

Duplicate Session clip to Arrangement.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `track` | object | yes |  |
| `clip` | object | yes |  |
| `destination_time` | number | yes |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_envelope`

Inspect or edit a clip automation envelope for one parameter.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `parameter` | object | yes |  |
| `create` | boolean |  |  |
| `clear` | boolean |  |  |
| `delete_range` | object |  |  |
| `insert_steps` | array |  |  |
| `start_time` | number |  |  |
| `end_time` | number |  |  |
| `limit` | integer |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_velocity_envelope`

Map note velocities to automation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `parameter` | object | yes |  |
| `min_value` | number |  |  |
| `max_value` | number |  |  |
| `invert` | boolean |  |  |
| `clear` | boolean |  |  |
| `step_duration` | number |  |  |
| `start_time` | number |  |  |
| `end_time` | number |  |  |
| `limit` | integer |  |  |
| `expected_set_signature` | string |  |  |

## `live_clip_warp_markers`

Inspect or edit audio clip warp state and markers.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `warping` | boolean |  |  |
| `warp_mode` | integer |  |  |
| `add_markers` | array |  |  |
| `move_markers` | array |  |  |
| `remove_beat_times` | array |  |  |
| `limit` | integer |  |  |
| `expected_set_signature` | string |  |  |

## `live_track_create_audio_clip`

Create Arrangement audio clip.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `file_path` | string | yes |  |
| `destination_time` | number | yes |  |
| `name` | string |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_track_insert_device`

Insert built-in Live device.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `device_name` | string | yes |  |
| `device_index` | integer |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_agent_audio_tap`

AgentAudioTap: command open/start/stop/status; start with path; UDP optional.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `command` | string | yes |  |
| `path` | string |  |  |
| `id` | string |  |  |
| `udp` | boolean |  |  |

## `live_agent_audio_tap_setup`

Load AgentAudioTap; solo target track; verify.

No parameters.

## `live_visual_capture`

Ableton Live window-only; device-detail crop/downscale; region-rel; no arbitrary apps/windows.

No parameters.

## `live_max_console_capture`

Max Console ('Max for Live' window) as an image: Max errors/post() the LOM hides. Opts: display=<n>/backend/list_only, crop/downscale.

No parameters.

## `live_agent_m4l_device`

arbitrary native UI, jweb/jbrowser web UI; wait_status compact_status compact_result status_state_keys web diag.

No parameters.

## `live_agent_m4l_cleanup`

Dry-run/delete AgentM4L; ask before delete.

No parameters.

## `live_transport`

Transport status/play/continue/stop; seek.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `action` | string |  |  |
| `time` | number |  |  |
| `timeout` | number |  |  |
| `strict_timeout` | boolean |  |  |

## `live_batch`

Batch ops.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | yes |  |
| `continue_on_error` | boolean |  |  |
| `include_traceback` | boolean |  |  |
| `expected_set_signature` | string |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |
| `strict_timeout` | boolean |  |  |

## `live_browser_roots`

List app.browser roots.

No parameters.

## `live_browser_capabilities`

Browser roots/filter types/semantic API exposure.

No parameters.

## `live_browser_search`

Bounded browser search.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string |  |  |
| `roots` | array |  | incl plugins |
| `limit` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_visited` | integer |  |  |
| `loadable_only` | boolean |  |  |
| `include_folders` | boolean |  |  |
| `stop_on_limit` | boolean |  |  |
| `stop_score` | integer |  |  |
| `match_all_terms` | boolean |  |  |

## `live_browser_load`

Load BrowserItem.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item` | object | yes |  |
| `target_track` | object |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_load_device`

Find device/preset by name in indexed browser (User Library/Places), load onto track; replaces dragging .amxd. path_contains disambiguates same-named matches; ambiguous->candidates. roots default user_folders+user_library.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes |  |
| `path_contains` | string |  |  |
| `name_exact` | boolean |  |  |
| `target_track` | object |  |  |
| `roots` | array |  |  |
| `max_depth` | integer |  |  |
| `max_visited` | integer |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |

## `live_browser_preview`

Preview or stop previewing a BrowserItem.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item` | object |  |  |
| `stop` | boolean |  |  |

## `find_similar_sounds`

Find similar sounds from Live 12+ local sound-analysis DB.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `base` | string |  |  |
| `query` | string |  |  |
| `limit` | integer |  |  |
| `include_self` | boolean |  |  |
| `db_path` | string |  |  |

## `live_prep_vocal_sample`

Trim silence from a vocal sample and transcribe it.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | yes |  |
| `output_dir` | string |  |  |
| `trim` | boolean |  |  |
| `silence_thresh_db` | number |  |  |
| `transcribe` | boolean |  |  |
| `model` | string |  | faster-whisper model size, e.g. tiny/base/small. |

## `live_eval`

Eval expression; use live_exec.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expr` | string | yes |  |
| `ref` | object |  |  |
| `allow_legacy_note_api` | boolean |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |

## `live_exec`

Run Live Python statements.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes |  |
| `ref` | object |  |  |
| `allow_legacy_note_api` | boolean |  |  |
| `detail` | boolean |  |  |
| `max_items` | integer |  |  |
| `max_depth` | integer |  |  |
| `max_string_length` | integer |  |  |
| `timeout` | number |  |  |
| `expected_set_signature` | string |  |  |
| `strict_timeout` | boolean |  |  |

## `live_observe`

Add/remove property listener.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ref` | object | yes |  |
| `property` | string | yes |  |
| `enabled` | boolean | yes |  |

## `live_events`

Drain retained Live listener events.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `limit` | integer |  |  |

