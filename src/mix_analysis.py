from __future__ import annotations

import argparse
import itertools
import json
import wave
from pathlib import Path
from typing import Any

# Band edges in Hz. "mud" conventionally lives around 200-500 Hz.
BANDS: tuple[tuple[str, float, float], ...] = (
    ("sub", 20.0, 60.0),
    ("bass", 60.0, 120.0),
    ("low_mid", 120.0, 250.0),
    ("mud", 250.0, 500.0),
    ("mid", 500.0, 2000.0),
    ("high_mid", 2000.0, 5000.0),
    ("presence", 5000.0, 10000.0),
    ("air", 10000.0, 20000.0),
)
BANDS_NAMES = tuple(name for name, _, _ in BANDS)
FFT_SIZE = 4096


def read_wav_mono(path: str | Path) -> tuple[Any, int]:
    """Read a PCM WAV (16/24/32-bit) as a mono float array in [-1, 1] plus its sample rate."""
    import numpy as np

    with wave.open(str(path), "rb") as handle:
        channels, width, rate, frames = handle.getnchannels(), handle.getsampwidth(), handle.getframerate(), handle.getnframes()
        raw = handle.readframes(frames)
    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        packed = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        ints = packed[:, 0].astype(np.int32) | (packed[:, 1].astype(np.int32) << 8) | (packed[:, 2].astype(np.int32) << 16)
        ints = np.where(ints & 0x800000, ints - 0x1000000, ints)
        data = ints.astype(np.float64) / 8388608.0
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError("Unsupported WAV sample width: %d bytes (need 16/24/32-bit PCM; float WAV is not supported)" % width)
    if channels > 1:
        data = data[: len(data) // channels * channels].reshape(-1, channels).mean(axis=1)
    return data, rate


def band_energies(samples: Any, rate: int) -> dict[str, float]:
    """Average power per band over Hann-windowed FFT frames (Welch-style, 50% overlap)."""
    import numpy as np

    if len(samples) < FFT_SIZE:
        samples = np.pad(samples, (0, FFT_SIZE - len(samples)))
    window = np.hanning(FFT_SIZE)
    hop = FFT_SIZE // 2
    starts = range(0, len(samples) - FFT_SIZE + 1, hop)
    power = np.zeros(FFT_SIZE // 2 + 1)
    count = 0
    for start in starts:
        power += np.abs(np.fft.rfft(samples[start : start + FFT_SIZE] * window)) ** 2
        count += 1
    power /= max(count, 1)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / rate)
    return {name: float(power[(freqs >= low) & (freqs < high)].sum()) for name, low, high in BANDS}


def _shares(energies: dict[str, float]) -> dict[str, float]:
    total = sum(energies.values())
    if total <= 0:
        return {name: 0.0 for name in energies}
    return {name: value / total for name, value in energies.items()}


def analyze_masking(paths: list[str], min_band_share: float = 0.15) -> dict[str, Any]:
    """Compare band-energy distributions of captured stems and report where they pile up.

    A band is "shared" by two tracks when each puts at least `min_band_share` of its own energy there;
    the pair's `overlap` is the sum over bands of the smaller share (0 = disjoint spectra, 1 = identical).
    This is an assistive heuristic on rendered audio, not a verdict.
    """
    if len(paths) < 1:
        raise ValueError("Give at least one WAV file")
    tracks: dict[str, dict[str, float]] = {}
    for path in paths:
        samples, rate = read_wav_mono(path)
        name = Path(path).stem
        while name in tracks:
            name += "_"
        tracks[name] = _shares(band_energies(samples, rate))

    summary = {
        name: {
            "dominant_band": max(shares, key=lambda band: shares[band]),
            "mud_share": round(shares["mud"], 3),
            "band_share": {band: round(value, 3) for band, value in shares.items()},
        }
        for name, shares in tracks.items()
    }
    pairs = []
    for (name_a, shares_a), (name_b, shares_b) in itertools.combinations(tracks.items(), 2):
        overlap = sum(min(shares_a[band], shares_b[band]) for band in shares_a)
        shared = [band for band in shares_a if shares_a[band] >= min_band_share and shares_b[band] >= min_band_share]
        pairs.append({"tracks": [name_a, name_b], "overlap": round(overlap, 3), "shared_bands": shared})
    pairs.sort(key=lambda pair: pair["overlap"], reverse=True)

    combined = {band: sum(shares[band] for shares in tracks.values()) / len(tracks) for band in BANDS_NAMES}
    return {
        "bands_hz": {name: [low, high] for name, low, high in BANDS},
        "tracks": summary,
        "pairs_by_overlap": pairs,
        "crowded_band": max(combined, key=lambda band: combined[band]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report frequency-band overlap between captured stems (e.g. AgentAudioTap WAVs).")
    parser.add_argument("files", nargs="+", help="PCM WAV files, one per track (16/24/32-bit).")
    parser.add_argument("--min-band-share", type=float, default=0.15, help="Min share of a track's energy for a band to count as shared.")
    args = parser.parse_args(argv)
    print(json.dumps(analyze_masking(args.files, args.min_band_share), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
