# Roadmap ideas

Research notes on the six unimplemented feature concepts listed in the README's
"Ideas" section. Each section covers: the feature concept, feasibility research
(Live Object Model classes/methods, libraries, prior art), an honest
feasibility/complexity assessment, an implementation sketch, and open
questions.

GitHub Issues are disabled on this repository, so these were written here
instead of filed as issues.

Filed from README's Ideas section during a repo review; not yet scheduled.

## 1. External hardware synth control: expose track I/O routing + MIDI CC/PC over the bridge

### Feature concept
Let the agent control external synthesizers/hardware from the MCP: create/configure an "External Instrument"-style track (MIDI out to hardware, audio in from hardware), and send MIDI CC/Program Change to hardware devices, all through natural-language requests.

### Research findings
- Live's own "External Instrument" device is the standard mechanism for this: it adds MIDI output routing (to a hardware synth) and audio input routing (back from the synth) on a single track. See Ableton's own doc, "Using hardware synthesizers with Live" (https://help.ableton.com/hc/en-us/articles/209774265-Using-hardware-synthesizers-with-Live) and the Reference Manual's Routing and I/O chapter (https://www.ableton.com/en/manual/routing-and-i-o/).
- The Live Object Model (LOM) exposes this at the `Track` level via `current_output_routing_type` / `available_output_routing_types` and the equivalent `*_input_routing_*` properties/`output_routing_channel`, `input_routing_channel` (see the LOM overview at https://docs.cycling74.com/legacy/max8/vignettes/live_object_model and the Max for Live routing reference at https://docs.cycling74.com/reference/live.routing). These are plain settable properties/dicts, not a special "hardware" API — routing a track's output to a MIDI port and its input from an audio interface channel is exactly how the External Instrument device itself is implemented under the hood.
- Sending arbitrary MIDI CC/PC to external gear is not exposed as a first-class LOM call for arbitrary ports; it typically goes through a MIDI clip/MIDI track's output routing (i.e., write MIDI notes/CC into a clip that's routed out to hardware) or through a Control Surface's own MIDI I/O. Notably, **this repo's bridge already is a Control Surface** (`AbletonLiveMCP(ControlSurface)` in `Ableton_Live_MCP/bridge.py`), which in principle has access to `_c_instance` MIDI send facilities the same way a real Remote Script (e.g. custom controller scripts) sends SysEx/CC to hardware — see the community docs at https://midiremotescripts.structure-void.com/guides/architecture/. That path is currently unused by the bridge; today MIDI out only happens implicitly via track routing + clips.
- Community forum threads confirm this is a well-worn manual workflow already ("Controlling hardware via Live external instruments", https://forum.ableton.com/viewtopic.php?f=1&t=225888; "Add MIDI control to External Instrument!", https://forum.ableton.com/viewtopic.php?p=752658) — people are already doing this by hand in the UI, which is a good sign the LOM primitives are sufficient for the routing half.
- No other Ableton MCP fork (jpoindexter/ableton-mcp, uisato/ableton-mcp-extended, Simon-Kansara/ableton-live-mcp-server, MCPBlender/ableton-mcp) appears to have shipped explicit hardware-routing tools; this would be differentiating.

### Feasibility / complexity assessment
- **Routing setup (create an External Instrument-equivalent track, point output at a MIDI port, input at an audio channel): straightforward.** These are plain LOM `Track` properties already reachable today via the repo's generic `live_get`/`live_set`/`live_call`/`live_eval`/`live_exec` tools — no new bridge RPC is strictly required, just discoverability (documented recipes + maybe a purpose-built helper for ergonomics).
- **Sending arbitrary CC/PC/SysEx directly out to a MIDI port (bypassing a clip) is unverified.** It would likely require using the ControlSurface's own MIDI output capability (`_send_midi` or similar, available to Remote Scripts) rather than the plain LOM. This needs a real Ableton + MIDI hardware setup to prototype/verify — cannot be blind-coded from docs alone.
- Enumerating available MIDI output ports (to know what "hardware" is even connected) needs verification of what `Song.available_output_routing_types` actually returns for a MIDI track with real hardware attached — again needs a live rig to test.

### Implementation sketch
- New MCP tool `live_track_setup_external_instrument(track_ref, midi_output, audio_input)` that resolves and sets `current_output_routing_type`/`current_input_routing_type` (and channel variants) in one call, returning the resulting routing state.
- New MCP tool (or extend `live_track_create_audio_clip`/clip tools) `live_send_midi_cc(track_ref or port, cc_number, value, channel)` for one-shot hardware control-change sends, backed by a new bridge RPC method that goes through the ControlSurface's MIDI-out path if the plain LOM doesn't support it.
- No new third-party dependencies expected; this stays inside the existing `Ableton_Live_MCP/bridge.py` Control Surface and `src/server.py` MCP tool layer.

### Open questions
- Does `_c_instance`/ControlSurface expose a documented way to send arbitrary MIDI messages out from a Remote Script that isn't tied to being the "active" control surface bank? Needs testing against real Ableton.
- Is per-hardware-device Program Change/SysEx (e.g., patch recall on a specific synth) even something this repo wants to model generically, or leave to the routing + clip-based CC automation that already works today?
- Should this be scoped down to "just make routing setup easy" for v1 and defer raw MIDI-out-of-band sends to a follow-up?

## 2. Guided mix-diagnosis Q&A ("why is my mix muddy?", "how do I sidechain?") grounded in the live set

### Feature concept
Let the agent answer open-ended mixing questions ("why does my mix sound muddy?", "how do I sidechain my bass to my kick?") by actually inspecting the current Live set — tracks, devices, levels, and audio content — rather than giving generic advice, and then optionally apply the fix (insert a Compressor with sidechain input, add an EQ cut, etc.).

### Research findings
- **Live has no built-in "why is my mix muddy" analysis API.** The LOM doesn't expose a mix-quality or frequency-masking score anywhere; this is confirmed by there being a whole market of third-party spectral-analysis tools/plugins for exactly this problem (TDR Prism's "Auditory Masking Mode", HoRNet SpectraDuck, Anthesis Spectral Sidechain — see https://integraudio.com/best-spectrum-analyzer-plugins/ and https://lame.buanzo.org/max4live_blog/sculpting-frequencies-with-precision-exploring-anthesis-spectral-sidechain-in-ableton-live.html) and even a dedicated "AI production mentor" product, TrackSensei (https://tracksensei.com/), that does frequency-masking/kick-bass-clash diagnosis as its whole business.
- What Live *does* expose natively and is directly usable: the **Compressor's sidechain input** (`Sidechain On`, `Sidechain Gain`, `Sidechain EQ` params) and native EQ Eight/EQ Three devices, all reachable as ordinary `Device`/`DeviceParameter` objects via the LOM — i.e. once a diagnosis is made, *applying* the fix (insert Compressor, route track B as sidechain input, drop a notch at the muddy frequency) is straightforward with existing generic tooling.
- Community confirms "mud" is conventionally low-mid buildup around 200–500 Hz caused by frequency masking between competing sources (https://mixanalytic.com/guides/frequency-spectrum-analysis) — a workable heuristic definition, but detecting *which two tracks* are masking each other requires actual spectral analysis of rendered audio, not just Live's static set data.
- **This repo already has the missing piece half-built**: `m4l/AgentAudioTap.amxd` (documented in README's "Built in Agent Audio Tap" section) lets the agent capture the audio signal at any point in the chain, and the existing workflow (per the piano-track spectrogram demo in the README) is "capture audio → run custom Python analysis → tweak devices → repeat." A "why is my mix muddy" tool is really "AgentAudioTap capture of 2+ tracks + FFT/energy-in-band comparison, in Python, off-repo" wired into a guided prompt/tool, not a new Live API surface.

### Feasibility / complexity assessment
- **Diagnosis of "which frequency bands are congested" — straightforward-to-medium.** Capture stems via AgentAudioTap (already built), compute band energy/masking overlap in Python (numpy/scipy FFT, no new heavyweight deps), and report back. No mix-quality LOM API exists, so this must be done out-of-band via audio capture, not asked from Live directly.
- **"How do I sidechain X to Y" — straightforward.** This is pure LOM device/parameter manipulation (insert Compressor, set `Sidechain On` + route input) using tooling this repo already has (`live_track_insert_device`, `live_device_parameters`, `live_parameter_set`).
- **General open-ended "why does my mix sound muddy" as a robust, always-correct diagnosis — hard.** Real mixing judgment (is it arrangement, is it one instrument, is it genuinely EQ) isn't reducible to a formula; this needs a real Ableton project with representative audio to prototype/tune thresholds against, and should be scoped as "assistive heuristic + agent reasoning," not a deterministic verdict.

### Implementation sketch
- New MCP tool `live_analyze_frequency_masking(tracks: [ref], band_edges?, tap_config?)`: uses AgentAudioTap to capture N tracks (soloed or via existing tap/solo target flow already in the bridge — see `_rpc_agent_audio_tap` in `Ableton_Live_MCP/bridge.py`), computes per-band RMS/energy overlap, returns a compact JSON summary (e.g. "Track A and Track C overlap heavily in 200-500Hz").
- New MCP tool `live_sidechain_setup(source_ref, target_ref, device="Compressor")`: inserts/configures a Compressor on `target_ref` with sidechain input routed from `source_ref`, using existing `live_track_insert_device` + `live_parameter_set`.
- A guided-prompt layer (could just be README/system-prompt guidance rather than code) telling the agent: "for mud/masking questions, call live_analyze_frequency_masking before answering; for sidechain questions, call live_sidechain_setup or explain + offer to apply."
- New Python dependency: numpy (or reuse whatever AgentAudioTap capture pipeline already uses) for FFT/band-energy computation — check `scripts/ableton_similar_sounds.py` and the audio-tap capture path for what's already in the dependency graph.

### Open questions
- What captured-audio format/sample rate does AgentAudioTap actually hand back today, and is it already sufficient for FFT analysis without new plumbing? Needs code-level check against `m4l/agent_audio_tap.js` and the bridge's tap RPCs.
- Should "mud" detection be track-pairwise (expensive, O(n^2) captures) or whole-mix band-energy analysis (cheaper, less specific)? Needs real-set experimentation to decide.
- Is there value in wiring in a real reference (TrackSensei-style) frequency-masking heuristic table, or is generic band-energy-overlap good enough for v1?

## 3. Auto-generate a chord track that harmonizes an existing MIDI melody

### Feature concept
Given an existing MIDI melody clip in the Live set, have the agent generate a matching chord progression on a new MIDI track/clip (e.g. "add a chord track that fits my melody", or "give me a backing track to noodle over").

### Research findings
- This is explicitly requested by real Ableton users and *not* natively supported: Live has no built-in chord-track feature (unlike Cubase/Studio One), confirmed by multiple open Ableton forum feature-request threads — "CHORD TRACK" (https://forum.ableton.com/viewtopic.php?t=246499), "Automatic chord & chord progression generators" (https://forum.ableton.com/viewtopic.php?f=1&t=92671), "Compose a melody on chords" (https://forum.ableton.com/viewtopic.php?t=224966). There's even a paid third-party Max for Live device for this exact use case, "gptx harmony transformation" (https://toolblox.gumroad.com/l/gptx-harmony-transformation), which is direct evidence of unmet demand and technical feasibility as an M4L/external add-on.
- The LOM itself has zero music-theory intelligence — no key/scale detection, no chord-fitting API. `Clip.get_notes_extended`/the note-list this repo already reads via `live_clip_notes` is just raw (pitch, start_time, duration, velocity) tuples; harmonization has to happen entirely in agent-side/Python logic, not in Live.
- For the actual algorithm, standard tooling exists: **music21** (harmonic analysis, key/scale utilities, roman-numeral chord generation — a mature, well-documented MIT-affiliated library) and **mingus** (simpler chord/scale primitives, historically used alongside music21 per community write-ups) are the two most-cited Python libraries for this. A blog walkthrough on generating tonal material combines "music21 for the piano score, mingus for chords" as a practical pairing.
- Realistically the agent doesn't strictly need a symbolic library at all — given the LLM's own music-theory knowledge plus the raw note list already exposed by `live_clip_notes`, it could infer key/scale and propose chords itself, then write them back with the existing `live_clip_add_notes`. A library like music21 would mainly help with *validating* the agent's guess (confirm key signature, confirm chord tones are diatonic) rather than being strictly required to generate anything.

### Feasibility / complexity assessment
- **Straightforward, and this repo already has all the mechanical pieces.** Reading notes (`live_clip_notes`), figuring out key/chords (either LLM reasoning or a music21 pass), creating a new MIDI track/clip and writing notes back (`live_track_insert_device`-style track creation + `live_clip_add_notes`) are all already-shipped tools — this is arguably the easiest of the six ideas to build, and needs no new bridge RPCs at all.
- The only real open question is *quality*: whether an LLM-reasoned chord progression from raw note timing/pitch data is musically convincing without a symbolic-theory library backing it up. That's a prompting/algorithm-design question, not an Ableton API question, and can be iterated on without a live Ableton install (can be prototyped against exported MIDI/note JSON offline).

### Implementation sketch
- No new bridge RPC needed — compose from existing tools: `live_clip_notes` (read melody) → agent or `music21`-backed Python analysis (infer key + propose chord-per-bar/phrase) → `live_track_insert_device`/new-track creation + `live_clip_add_notes` (write the chord clip).
- Optional: a small helper script (like `scripts/ableton_similar_sounds.py`'s pattern) e.g. `scripts/suggest_chords.py` that takes a note-list JSON and returns a chord-progression JSON, callable by the agent, using `music21` if added as an optional dependency.
- New dependency (optional, only if we want algorithmic validation rather than pure LLM reasoning): `music21` (pure Python, MIT-style license, no native/system deps — safe to add).

### Open questions
- Pure-LLM-reasoning vs. music21-assisted: is the added dependency worth it, or does the agent already do fine reasoning about key/scale from a note-events JSON directly?
- Should the generated chord clip be on a new instrument track (with a default Live keyboard/pad instrument inserted), or should it require the user to pick a device first?
- How should phrasing/chord-change timing be chosen (per-bar? per detected melodic phrase boundary?) — needs a few real test melodies to tune, ideally against an actual Live set.

### Resolution: no new tool needed for v1

Checked what "known pools" existed for this before building anything: the real prior art
(sander-wood/autoharmonizer, billyblu2000/AccoMontage2) are full research codebases with
trained model weights and their own inference pipelines — disproportionate to bolt onto a
lightweight MCP bridge for what's fundamentally "suggest some chords for this melody."

This repo already has every mechanical piece this feature needs: `live_clip_notes` to read
the melody, and `live_clip_add_notes` to write the chord clip. The missing piece isn't a new
tool, it's a **recipe** — telling the agent to read the melody, reason about key/chords
itself (an LLM already does this reasonably well from a raw note-events JSON), and write the
result back. Recommended prompt-level recipe, for AGENTS.md/system-prompt guidance rather
than new code:

1. `live_clip_notes` on the melody clip to get the raw (pitch, start_time, duration) events.
2. Infer the key/scale and a chord-per-bar (or per phrase) progression from those events using
   ordinary music-theory reasoning — no library required for v1.
3. Create a new MIDI track/clip (existing track-creation tooling) and `live_clip_add_notes` to
   write the chord voicings in.

If chord suggestions from pure LLM reasoning turn out to be unreliable in practice, revisit
with `music21` (pure Python, MIT-style license, no native deps — safe to add) as a validation
pass rather than a generation engine — confirm diatonic-ness of the guessed chords, not invent
them from scratch.

## 4. Vocal sample prep pipeline: trim silence + transcribe before creative reuse

### Feature concept
Let the agent take existing vocal sample files, trim leading/trailing silence, transcribe the speech/singing content (so the agent knows what's being said and can reason about it), and then creatively incorporate the cleaned/transcribed samples into the Live set (e.g. as chopped one-shots, arranged into a new phrase, etc).

### Research findings
- **Silence trimming**: two standard, well-documented Python approaches. `librosa.effects.trim` trims leading/trailing silence based on an amplitude threshold (does not remove internal silence); `pydub.silence.split_on_silence` (with `min_silence_len`/`silence_thresh` params) is the standard approach for splitting/removing silence including internal gaps, per multiple tutorials (e.g. https://noobest.medium.com/silence-trimmer-your-first-speech-audio-processing-exercise-in-python-1cc48a2a466b, https://codesignal.com/learn/courses/transcribing-large-files-in-python-using-pydub/lessons/introduction-to-audio-processing-with-pydub). More robust option for speech specifically: VAD-based silence removal (Malaya-Speech's VAD docs, https://malaya-speech.readthedocs.io/en/latest/remove-silent-vad.html), which handles noisy/breathy vocal takes better than a flat amplitude threshold.
- **Transcription**: OpenAI's Whisper is the clear standard tool cited everywhere for this (https://en.wikipedia.org/wiki/Whisper_(speech_recognition_system)); OpenAI's own cookbook has a guide specifically on pre/post-processing around Whisper (https://developers.openai.com/cookbook/examples/whisper_processing_guide), and multiple write-ups note that untrimmed leading silence can cause Whisper to mistranscribe — i.e. **silence-trimming should happen before transcription**, confirming the natural pipeline order (trim → transcribe, not the reverse).
- This repo doesn't currently touch raw audio *files* at all in a general way — `find_similar_sounds` (`src/similar_sounds.py`) reads Ableton's own precomputed analysis DB (`Live-files-*.db`) rather than decoding audio itself, and there's no existing librosa/pydub/whisper dependency in `pyproject.toml`. `live_track_create_audio_clip` (bridge RPC `track_create_audio_clip`) can already place a *given* audio file onto a track/into the Arrangement, so the "incorporate into the Live set" half is solved — what's missing is everything upstream of that (loading, trimming, and transcribing the source file).
- Whisper models can run fully offline/locally (no API key needed for the open-source model), which matters for a tool meant to run unattended inside an agent loop.

### Feasibility / complexity assessment
- **Straightforward overall, and cleanly decomposable.** All three stages (trim, transcribe, place-in-set) are well-trodden with mature, permissively-licensed open-source tools; none require anything from the Live Object Model beyond the file-placement step this repo already has. No Ableton-specific unknowns here — this is standard Python audio-processing plumbing, and unlike ideas #1/#2/#5 it does **not** need a live Ableton install to prototype the hard part (trim+transcribe can be fully developed/tested against sample WAV files with no DAW open at all).
- Main practical risk is dependency weight: `openai-whisper` pulls in PyTorch, which is a heavy, large binary dependency for what's otherwise a lightweight bridge package — worth deciding whether to make it optional (extras group) rather than a hard dependency.

### Implementation sketch
- New MCP tool `live_prep_vocal_sample(file_path, output_dir?, min_silence_len?, silence_thresh?, model="base")`: runs pydub/librosa-based silence trim, then runs Whisper transcription, returns `{trimmed_path, transcript, segments}` as JSON — this can live entirely in `src/` (pure Python helper, like `src/similar_sounds.py`'s pattern) with no bridge RPC needed since it doesn't touch Live at all until the final placement step.
- Reuse existing `live_track_create_audio_clip` to place the trimmed file once ready.
- New dependencies, as an optional extra (e.g. `pip install ableton-live-mcp[vocals]`): `pydub` (+ system `ffmpeg`, which pydub shells out to), `librosa` (optional, if VAD-quality trimming is wanted over pydub's threshold split), and `openai-whisper` (or a lighter alternative like `faster-whisper`/`whisper.cpp` bindings to avoid the full PyTorch dependency — worth evaluating both).

### Open questions
- `openai-whisper` (PyTorch-based) vs `faster-whisper` (CTranslate2-based, much smaller/faster, no PyTorch) — which to standardize on, given this repo seems to otherwise avoid heavy dependencies?
- Should trimming target only leading/trailing silence (`librosa.effects.trim`) or also chop out internal silence/breaths (`pydub.silence.split_on_silence`) to produce multiple one-shots from one longer take? Probably both should be supported via a parameter.
- Does `ffmpeg` availability need to be checked/documented as a system prerequisite (pydub requires it for non-WAV formats)?

## 5. User-controlled DJ effects/performance macros (crossfader, cue, macro racks)

### Feature concept
"Crazy user-controlled DJ effects": set up performance-oriented controls in a live set — crossfader assignments between track groups, cue/preview soloing like a DJ mixer, and macro-mapped effect racks (filter sweeps, beat-repeat, etc.) that a user can drive live, with the agent doing the setup work.

### Research findings
- Live has a **real, native DJ-mixer-style feature set** this maps onto directly, not just a metaphor: the Main track's crossfader "works like a typical DJ-mixer crossfader, except it allows crossfading not only two, but any number of tracks — including the returns" (Ableton Reference Manual, Mixing chapter: https://www.ableton.com/en/manual/mixing/). Each track has an A/B crossfade assignment control, and Live also supports replacing normal solo with **cueing** — "lets you preview tracks as though you were cueing a record on a DJ mixer" (https://www.soundonsound.com/techniques/cueing-crossfading-ableton-live, forum thread "Cueing in Ableton": https://forum.ableton.com/viewtopic.php?t=225293).
- In the LOM, this is exposed via `Track.mixer_device.crossfade_assign` (A/None/B) and `Song.master_track` / the crossfader's own automatable parameter on the Main track's Mixer device ("Crossfade" chooser) — same `DeviceParameter` mechanism as every other mixer control, per the LOM overview (https://docs.cycling74.com/legacy/max8/vignettes/live_object_model). Push hardware exposes user-mode crossfader control too (forum: "Crossfader Control in Push", https://forum.ableton.com/viewtopic.php?t=204847) confirming it's a first-class mixer parameter, not a hidden/undocumented feature.
- "Macro racks" (Audio/Instrument/MIDI Effect Racks with up to 16 assignable Macro knobs mapped to any nested device parameter) are Live's standard mechanism for building a single "performance knob" that morphs multiple parameters together — exactly the kind of "crazy DJ effect" (e.g. one macro sweeping a Filter + Reverb send + Beat Repeat chance together) users mean by this idea. Macros are ordinary `DeviceParameter` objects on a `RackDevice`, reachable with the same generic parameter tools this repo already ships.
- No dedicated "DJ mode" object/API beyond the above was found in Live 12; the crossfader/cueing features are just specific facets of the standard Mixer/Track API, not a separate subsystem.

### Feasibility / complexity assessment
- **Straightforward — this is almost entirely composable from tooling this repo already has.** Crossfade assignment (`crossfade_assign` on `MixerDevice`), cueing/solo state, and Macro rack parameter mapping are all plain LOM properties/`DeviceParameter`s already reachable via `live_get`/`live_set`/`live_call`/`live_device_parameters`/`live_parameter_set` and rack insertion via `live_track_insert_device`. No fundamentally new Live API surface is required.
- The only "hard" part is UX/design, not API access: choosing sensible default macro mappings for a "crazy" performance effect (e.g. what should map to what for a satisfying filter-sweep-into-beat-repeat macro) is a creative/musical judgment call, not a technical blocker, and benefits from testing against a real Live set with real devices to hear whether the mapped ranges actually sound good.

### Implementation sketch
- New MCP tool `live_track_set_crossfade_assign(track_ref, assign)` (A/None/B) — thin wrapper over `mixer_device.crossfade_assign`.
- New MCP tool `live_rack_map_macro(rack_ref, macro_index, target_param_refs, ranges)` to wire multiple nested `DeviceParameter`s to one Macro, since multi-parameter macro-mapping via raw `live_exec` is possible today but fiddly (needs `RackDevice.macros`, `chain_selector`, and per-chain-device parameter mapping calls) — a purpose-built helper would make this materially easier for the agent to use reliably.
- Possibly a small library of "recipe" macro setups (e.g. "filter+reverb+repeat performance macro") the agent can offer as starting points, expressed as JSON specs rather than new bridge RPCs.
- No new third-party dependencies expected.

### Open questions
- Is `crossfade_assign` settable via the generic `live_set` tool already today without a dedicated helper, or does it need special-casing (e.g. enum validation)? Needs a quick check against a real Live set.
- Should "cueing" mode (replacing solo-as-preview) be something this repo toggles (`Song` has a cue-related preference?) or is it purely a UI/manual-workflow feature not reachable from the LOM at all — needs verification against real Live, since the SOS article describes it as a workflow/preference rather than a scriptable object.
- How opinionated should default "DJ effect" macro recipes be vs. just exposing the raw mapping primitive and letting the agent/LLM design the mapping per request?

## 6. VJ integration: drive Videosync visuals from the live set via device parameters

### Feature concept
"Experiment with VJ plugins like Videosync to make music videos driven by your live set" — let the agent set up and control a VJ tool (Videosync specifically, or similar) so visuals react to/are driven by the actual Live set (tracks, clips, automation), for music-video generation.

### Research findings
- **Videosync (by Showsync) is itself a Max for Live device that lives inside Ableton Live**, not a separate external application needing OSC/network bridging — per its own site (https://www.showsync.com/videosync/) it's "a deep Max for Live visual engine" with "integration with Ableton Live's native interface, modulation, Warp Markers, and edit/play workflows," and it can be triggered by MIDI notes via a "Video Simpler" that mimics Ableton's own Simpler instrument. CDM's coverage confirms this integration depth: "Videosync 1.0 arrives: visuals integrate with Ableton Live Session, Arrangement, Warping" (https://cdm.link/videosync-1-0-arrives-visuals-integrate-with-ableton-live-session-arrangement-warping/) and a 2.1 update adding a video recorder/monitor (https://cdm.link/videosync-2-1-for-ableton-live/).
- Because it's an M4L device, its exposed controls are ordinary `Device`/`DeviceParameter` objects in the Live Object Model, automatable the same way as any other device — Cycling '74 has an official tutorial "Creating Videosync Plug-Ins in Max for Live" (https://cycling74.com/tutorials/creating-videosync-plug-ins-in-max-for-live-ableton-live) describing how Videosync plug-ins declare new parameters via `videoDevice` abstractions and shader code, and a community Videosync device build is listed on maxforlive.com (https://maxforlive.com/library/device/6672/videosync). This means **this repo's existing generic device-parameter tooling (`live_device_parameters`, `live_parameter_set`, `live_track_insert_device`) should already be able to enumerate and drive a Videosync device's parameters once one is loaded on a track**, exactly like it drives any other device (including the repo's own `AgentAudioTap.amxd`).
- For non-Videosync / external VJ software (Resolume, VDMX, TouchDesigner, etc.), **Ableton Link** is the documented standard bridge for tempo/beat-phase sync without MIDI clock (CDM: "Now you can sync up live visuals with Ableton Link", https://cdm.link/2017/02/now-can-sync-live-visuals-ableton-link/), and Showsync separately offers **LiveGrabber**, which emits OSC messages for track/scene/clip/plugin changes (https://www.showsync.com/tools/) — a documented OSC surface for driving external visual software from a Live set, independent of Videosync.
- One community repo, `hsien-hsiuliao/ableton-unreal-engine`, exists as prior art for driving a game-engine-based visual tool from Ableton, suggesting the "DAW state → visuals" pattern has been attempted before outside this project too.

### Feasibility / complexity assessment
- **If scoped to Videosync specifically: likely straightforward, reusing 90% existing tooling — but unverified without a real Ableton + Videosync install.** Since Videosync is "just" an M4L device on a track, this repo's existing `live_track_insert_device` (to load it, if it's discoverable via the browser like other devices) and `live_device_parameters`/`live_parameter_set` (to read/drive its shader/video parameters) should work with zero new bridge RPCs — but this is an assumption based on how M4L devices generally work, not confirmed against Videosync's actual parameter set, which needs a licensed Videosync install to verify (it's a commercial product, not bundled with Live).
- **If scoped to arbitrary external VJ software (Resolume/VDMX/TouchDesigner): medium-hard.** This repo would need to either (a) send Ableton Link timing (not something the LOM/this bridge currently touches at all — would need a new dependency/integration with the Link SDK) or (b) emit OSC messages itself (the repo has no existing OSC layer; Showsync's own LiveGrabber already does this and could arguably just be recommended alongside this MCP rather than reimplemented).
- Overall: **needs a real Ableton install with Videosync licensed and loaded to prototype and verify parameter names/behavior — cannot be blind-coded from docs alone**, same caveat as ideas #1 and #2.

### Implementation sketch
- v1 (Videosync-in-Live path): no new bridge RPC — just verify + document that `live_browser_search`/`live_track_insert_device` can find and load a Videosync device (if licensed/installed) and that `live_device_parameters`/`live_parameter_set` correctly enumerate/drive its parameters, same as any other device. Possibly add example "recipes" (map a Videosync shader parameter to a track's output level via `live_clip_envelope`/automation) to the agent-facing instructions, no code changes needed.
- v2 (external VJ software path, optional/bigger): new bridge capability or standalone helper for Ableton Link output (new dependency: the Link C++ SDK or a Python binding like `abl_link`), or an OSC-sender helper (new dependency: `python-osc`) mirroring what LiveGrabber already does — likely lower priority given Showsync's own tool already covers this.

### Open questions
- Does Videosync's device actually expose musically-useful automatable parameters via the standard LOM `DeviceParameter` list, or are some of its controls Max-patcher-internal and not LOM-visible? Needs a real install to check.
- Is it in scope for this MCP to reimplement Ableton Link/OSC output, given LiveGrabber (from the same vendor as Videosync) already exists and does this? Might be better to just document "use LiveGrabber alongside this MCP" rather than duplicate it.
- Should this be reframed more narrowly as "drive any M4L device's parameters from automation/agent commands" (a generic capability, of which Videosync is just one example) rather than a Videosync-specific feature?
