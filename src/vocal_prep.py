from __future__ import annotations

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
