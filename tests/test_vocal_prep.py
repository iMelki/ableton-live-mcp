from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from vocal_prep import prep_vocal_sample


def make_wav(path: Path, silence_ms: int = 300, tone_ms: int = 200, frame_rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(frame_rate)
        silence = [0] * int(frame_rate * silence_ms / 1000)
        tone = [8000 if i % 20 < 10 else -8000 for i in range(int(frame_rate * tone_ms / 1000))]
        samples = silence + tone + silence
        handle.writeframes(struct.pack("<%dh" % len(samples), *samples))


def test_prep_vocal_sample_trims_leading_and_trailing_silence(tmp_path):
    source = tmp_path / "take.wav"
    make_wav(source, silence_ms=300, tone_ms=200)

    result = prep_vocal_sample({"file_path": str(source), "transcribe": False})

    assert result["source_path"] == str(source)
    assert Path(result["trimmed_path"]).exists()
    assert result["trimmed_duration_ms"] < result["original_duration_ms"]
    # Should be close to the 200ms tone region, not the original ~800ms.
    assert result["trimmed_duration_ms"] < 400


def test_prep_vocal_sample_can_skip_trim(tmp_path):
    source = tmp_path / "take.wav"
    make_wav(source, silence_ms=300, tone_ms=200)

    result = prep_vocal_sample({"file_path": str(source), "trim": False, "transcribe": False})

    assert result["trimmed_duration_ms"] == result["original_duration_ms"]


def test_prep_vocal_sample_uses_injected_transcriber(tmp_path):
    source = tmp_path / "take.wav"
    make_wav(source)
    calls = []

    def fake_transcribe(path):
        calls.append(path)
        return {"text": "hello world", "language": "en", "segments": [{"start": 0.0, "end": 0.2, "text": "hello world"}]}

    result = prep_vocal_sample({"file_path": str(source)}, transcribe_fn=fake_transcribe)

    assert calls == [Path(result["trimmed_path"])]
    assert result["transcript"] == "hello world"
    assert result["language"] == "en"
    assert result["segments"] == [{"start": 0.0, "end": 0.2, "text": "hello world"}]


def test_prep_vocal_sample_writes_to_output_dir(tmp_path):
    source = tmp_path / "in" / "take.wav"
    source.parent.mkdir()
    make_wav(source)
    output_dir = tmp_path / "out"

    result = prep_vocal_sample(
        {"file_path": str(source), "output_dir": str(output_dir), "transcribe": False},
    )

    assert Path(result["trimmed_path"]).parent == output_dir
    assert Path(result["trimmed_path"]).exists()


def test_prep_vocal_sample_requires_file_path():
    with pytest.raises(ValueError):
        prep_vocal_sample({})


def test_prep_vocal_sample_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        prep_vocal_sample({"file_path": str(tmp_path / "missing.wav")})
