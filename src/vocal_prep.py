from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

TranscribeFn = Callable[[Path], dict[str, Any]]


def trim_silence(segment: Any, silence_thresh_db: float = -40.0, chunk_size_ms: int = 10) -> Any:
    from pydub.silence import detect_leading_silence

    start_trim = detect_leading_silence(segment, silence_threshold=silence_thresh_db, chunk_size=chunk_size_ms)
    end_trim = detect_leading_silence(segment.reverse(), silence_threshold=silence_thresh_db, chunk_size=chunk_size_ms)
    duration = len(segment)
    if start_trim + end_trim >= duration:
        return segment[0:0]
    return segment[start_trim : duration - end_trim]


def _default_transcriber(model_size: str) -> TranscribeFn:
    def transcribe(path: Path) -> dict[str, Any]:
        # Requires the optional `vocals` extra (`pip install ableton-live-mcp[vocals]`).
        from faster_whisper import WhisperModel

        model = WhisperModel(model_size)
        segments, info = model.transcribe(str(path))
        segments = list(segments)
        return {
            "text": "".join(segment.text for segment in segments).strip(),
            "language": info.language,
            "segments": [{"start": segment.start, "end": segment.end, "text": segment.text.strip()} for segment in segments],
        }

    return transcribe


def prep_vocal_sample(params: dict[str, Any] | None = None, transcribe_fn: TranscribeFn | None = None) -> dict[str, Any]:
    params = params or {}
    file_path = params.get("file_path")
    if not file_path:
        raise ValueError("file_path is required")
    source = Path(file_path)
    if not source.is_file():
        raise FileNotFoundError("No such audio file: %s" % source)

    from pydub import AudioSegment

    segment = AudioSegment.from_file(source)
    original_ms = len(segment)

    if params.get("trim", True):
        silence_thresh_db = float(params.get("silence_thresh_db", -40.0))
        segment = trim_silence(segment, silence_thresh_db=silence_thresh_db)

    output_dir = Path(params["output_dir"]) if params.get("output_dir") else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    trimmed_path = output_dir / ("%s.trimmed.wav" % source.stem)
    segment.export(trimmed_path, format="wav")

    result: dict[str, Any] = {
        "source_path": str(source),
        "trimmed_path": str(trimmed_path),
        "original_duration_ms": original_ms,
        "trimmed_duration_ms": len(segment),
    }

    if params.get("transcribe", True):
        transcribe = transcribe_fn or _default_transcriber(str(params.get("model", "base")))
        transcription = transcribe(trimmed_path)
        result["transcript"] = transcription.get("text", "")
        result["language"] = transcription.get("language")
        result["segments"] = transcription.get("segments", [])

    return result


def threshold_sweep(file_path: str, thresholds: tuple[float, ...] = (-30.0, -35.0, -40.0, -45.0, -50.0, -55.0, -60.0)) -> dict[str, Any]:
    """Show how much silence each `silence_thresh_db` removes from a real take, to help pick a default."""
    from pydub import AudioSegment

    source = Path(file_path)
    if not source.is_file():
        raise FileNotFoundError("No such audio file: %s" % source)
    segment = AudioSegment.from_file(source)
    rows = []
    for threshold in thresholds:
        trimmed = trim_silence(segment, silence_thresh_db=threshold)
        rows.append({"silence_thresh_db": threshold, "trimmed_ms": len(trimmed), "removed_ms": len(segment) - len(trimmed)})
    return {"source": str(source), "original_ms": len(segment), "sweep": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trim silence from (and optionally transcribe) a vocal sample.")
    parser.add_argument("file", help="Path to the audio file (WAV works everywhere; other formats need ffmpeg).")
    parser.add_argument("--sweep", action="store_true", help="Only report how much each silence threshold would trim; writes nothing.")
    parser.add_argument("--silence-thresh-db", type=float, default=-40.0)
    parser.add_argument("--output-dir")
    parser.add_argument("--transcribe", action="store_true", help="Also transcribe (needs the 'vocals' extra: pip install -e '.[vocals]').")
    parser.add_argument("--model", default="base", help="faster-whisper model size, e.g. tiny/base/small.")
    args = parser.parse_args(argv)
    if args.sweep:
        result = threshold_sweep(args.file)
    else:
        params: dict[str, Any] = {"file_path": args.file, "silence_thresh_db": args.silence_thresh_db, "transcribe": args.transcribe, "model": args.model}
        if args.output_dir:
            params["output_dir"] = args.output_dir
        result = prep_vocal_sample(params)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
