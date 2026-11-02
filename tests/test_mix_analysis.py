from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from mix_analysis import analyze_masking, main, read_wav_mono

RATE = 44100


def write_wav(path: Path, signal, width: int = 2, channels: int = 1) -> None:
    signal = np.clip(signal, -1.0, 1.0)
    if channels == 2:
        signal = np.stack([signal, signal], axis=1).reshape(-1)
    if width == 2:
        raw = (signal * 32767).astype("<i2").tobytes()
    else:
        ints = (signal * 8388607).astype(np.int32)
        raw = b"".join(int(v & 0xFFFFFF).to_bytes(3, "little") for v in ints)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(RATE)
        handle.writeframes(raw)


def sine(freq: float, seconds: float = 1.0, amp: float = 0.4):
    t = np.arange(int(RATE * seconds)) / RATE
    return amp * np.sin(2 * np.pi * freq * t)


def test_overlapping_tracks_rank_above_disjoint_ones(tmp_path):
    write_wav(tmp_path / "bass.wav", sine(80))
    write_wav(tmp_path / "bass2.wav", sine(90))
    write_wav(tmp_path / "hats.wav", sine(8000))

    result = analyze_masking([str(tmp_path / n) for n in ("bass.wav", "bass2.wav", "hats.wav")])

    top = result["pairs_by_overlap"][0]
    assert top["tracks"] == ["bass", "bass2"]
    assert top["overlap"] > 0.9
    assert top["shared_bands"] == ["bass"]
    assert result["pairs_by_overlap"][-1]["overlap"] < 0.05
    assert result["tracks"]["hats"]["dominant_band"] == "presence"
    assert result["crowded_band"] == "bass"


def test_mud_share_flags_low_mid_buildup(tmp_path):
    write_wav(tmp_path / "pad.wav", sine(350))
    write_wav(tmp_path / "lead.wav", sine(1000))

    tracks = analyze_masking([str(tmp_path / "pad.wav"), str(tmp_path / "lead.wav")])["tracks"]

    assert tracks["pad"]["mud_share"] > 0.9
    assert tracks["lead"]["mud_share"] < 0.05


def test_reads_24_bit_and_stereo(tmp_path):
    write_wav(tmp_path / "wide.wav", sine(1000), width=3, channels=2)

    samples, rate = read_wav_mono(tmp_path / "wide.wav")

    assert rate == RATE
    assert len(samples) == RATE
    assert abs(samples).max() == pytest.approx(0.4, abs=0.01)


def test_rejects_float_wav_width(tmp_path):
    path = tmp_path / "bad.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(1)
        handle.setframerate(RATE)
        handle.writeframes(b"\x80" * 100)
    with pytest.raises(ValueError, match="Unsupported WAV sample width"):
        read_wav_mono(path)


def test_silent_track_does_not_divide_by_zero(tmp_path):
    write_wav(tmp_path / "silent.wav", np.zeros(RATE))
    write_wav(tmp_path / "tone.wav", sine(1000))

    result = analyze_masking([str(tmp_path / "silent.wav"), str(tmp_path / "tone.wav")])

    assert result["pairs_by_overlap"][0]["overlap"] == 0.0


def test_cli_prints_json(tmp_path, capsys):
    write_wav(tmp_path / "a.wav", sine(200))

    assert main([str(tmp_path / "a.wav")]) == 0

    assert '"crowded_band": "low_mid"' in capsys.readouterr().out
