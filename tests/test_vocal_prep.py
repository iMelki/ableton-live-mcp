from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from vocal_prep import ModelNotCachedError, main, prep_vocal_sample


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


def test_threshold_sweep_reports_monotonic_trimming(tmp_path):
    from vocal_prep import threshold_sweep

    source = tmp_path / "take.wav"
    make_wav(source, silence_ms=300, tone_ms=200)

    result = threshold_sweep(str(source))

    assert result["original_ms"] > 0
    removed = [row["removed_ms"] for row in result["sweep"]]
    assert removed == sorted(removed, reverse=True)  # stricter (lower) threshold never removes more
    assert all(row["trimmed_ms"] + row["removed_ms"] == result["original_ms"] for row in result["sweep"])


def test_cli_sweep_writes_nothing_and_prints_json(tmp_path, capsys):
    import json

    from vocal_prep import main

    source = tmp_path / "take.wav"
    make_wav(source)
    before = sorted(p.name for p in tmp_path.iterdir())

    assert main([str(source), "--sweep"]) == 0

    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert json.loads(capsys.readouterr().out)["sweep"]


def test_cli_trims_without_transcribing_by_default(tmp_path, capsys):
    import json

    from vocal_prep import main

    source = tmp_path / "take.wav"
    make_wav(source)

    assert main([str(source)]) == 0

    out = json.loads(capsys.readouterr().out)
    assert "transcript" not in out
    assert Path(out["trimmed_path"]).exists()


def _install_fake_faster_whisper(monkeypatch, calls, cached):
    import sys
    import types

    utils = types.ModuleType("faster_whisper.utils")

    def download_model(size, local_files_only=False):
        calls.append((size, local_files_only))
        if local_files_only and not cached:
            raise RuntimeError("not cached")
        return "/models/%s" % size

    utils.download_model = download_model
    package = types.ModuleType("faster_whisper")
    package.__path__ = []

    class WhisperModel:
        def __init__(self, path):
            calls.append(("load", path))

        def transcribe(self, _path):
            segment = types.SimpleNamespace(start=0.0, end=1.0, text=" hi ")
            return [segment], types.SimpleNamespace(language="en")

    package.WhisperModel = WhisperModel
    package.utils = utils
    monkeypatch.setitem(sys.modules, "faster_whisper", package)
    monkeypatch.setitem(sys.modules, "faster_whisper.utils", utils)


def test_transcribe_fails_fast_when_model_not_cached(tmp_path, monkeypatch):
    source = tmp_path / "take.wav"
    make_wav(source)
    calls: list = []
    _install_fake_faster_whisper(monkeypatch, calls, cached=False)

    with pytest.raises(ModelNotCachedError, match="--fetch-model --model base"):
        prep_vocal_sample({"file_path": str(source)})
    assert calls == [("base", True)]


def test_transcribe_uses_cached_model_without_download(tmp_path, monkeypatch):
    source = tmp_path / "take.wav"
    make_wav(source)
    calls: list = []
    _install_fake_faster_whisper(monkeypatch, calls, cached=True)

    result = prep_vocal_sample({"file_path": str(source), "model": "tiny"})

    assert result["transcript"] == "hi"
    assert calls == [("tiny", True), ("load", "/models/tiny")]


def test_allow_download_lets_the_model_download(tmp_path, monkeypatch):
    source = tmp_path / "take.wav"
    make_wav(source)
    calls: list = []
    _install_fake_faster_whisper(monkeypatch, calls, cached=False)

    prep_vocal_sample({"file_path": str(source), "allow_download": True})

    assert calls[0] == ("base", False)


def test_fetch_model_cli_downloads_and_exits(monkeypatch, capsys):
    calls: list = []
    _install_fake_faster_whisper(monkeypatch, calls, cached=False)

    assert main(["--fetch-model", "--model", "small"]) == 0

    assert calls == [("small", False)]
    assert '"path": "/models/small"' in capsys.readouterr().out


def test_transcribe_retries_on_cpu_when_cuda_runtime_missing(tmp_path, monkeypatch):
    import sys
    import types

    source = tmp_path / "take.wav"
    make_wav(source)
    calls: list = []
    _install_fake_faster_whisper(monkeypatch, calls, cached=True)
    package = sys.modules["faster_whisper"]
    base_model = package.WhisperModel

    class CudaBrokenModel(base_model):
        def __init__(self, path, device="auto", compute_type="default"):
            super().__init__(path)
            self.device = device

        def transcribe(self, _path):
            if self.device == "auto":
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
            segment = types.SimpleNamespace(start=0.0, end=1.0, text=" hi ")
            return [segment], types.SimpleNamespace(language="en")

    package.WhisperModel = CudaBrokenModel

    assert prep_vocal_sample({"file_path": str(source)})["transcript"] == "hi"


def test_transcribe_does_not_swallow_unrelated_runtime_errors(tmp_path, monkeypatch):
    import sys

    source = tmp_path / "take.wav"
    make_wav(source)
    _install_fake_faster_whisper(monkeypatch, [], cached=True)

    def boom(self, _path):
        raise RuntimeError("something else")

    monkeypatch.setattr(sys.modules["faster_whisper"].WhisperModel, "transcribe", boom)

    with pytest.raises(RuntimeError, match="something else"):
        prep_vocal_sample({"file_path": str(source)})


def test_cli_reports_uncached_model_without_traceback(tmp_path, monkeypatch, capsys):
    source = tmp_path / "take.wav"
    make_wav(source)
    _install_fake_faster_whisper(monkeypatch, [], cached=False)

    assert main([str(source), "--transcribe"]) == 1

    assert "--fetch-model --model base" in capsys.readouterr().err
