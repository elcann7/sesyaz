from __future__ import annotations

import io
import math
import threading
import wave
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000


def list_input_devices() -> list[dict]:
    """Return deduplicated active Windows microphone input devices."""
    devices = sd.query_devices()
    default_in = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
    seen_names: set[str] = set()
    out: list[dict] = []
    for idx, d in enumerate(devices):
        if int(d.get("max_input_channels", 0)) <= 0:
            continue
        name = str(d.get("name", f"Microphone {idx}")).strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        out.append(
            {
                "index": idx,
                "name": name,
                "isDefault": idx == default_in,
                "sampleRate": int(d.get("default_samplerate", SAMPLE_RATE)),
            }
        )
    return out


class AudioRecorder:
    """Thread-safe 16kHz mono PCM recorder with smoothed real-time RMS level and PCM streaming."""

    def __init__(
        self,
        on_level: Optional[Callable[[float, list[float]], None]] = None,
        on_pcm: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        self._on_level = on_level
        self._on_pcm = on_pcm
        self._lock = threading.Lock()
        self._chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self._bands = [0.0] * 16

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, device_index: Optional[int] = None) -> None:
        with self._lock:
            if self._recording:
                return
            self._chunks = []
            self._bands = [0.0] * 16

            def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
                if not self._recording:
                    return
                mono = indata[:, 0].copy()
                self._chunks.append(mono)
                if self._on_pcm:
                    try:
                        self._on_pcm(mono.tobytes())
                    except Exception:
                        pass
                if self._on_level:
                    rms = float(np.sqrt(np.mean(np.square(mono.astype(np.float32) / 32768.0))))
                    norm = min(1.0, math.pow(rms * 5.2, 0.72))
                    # Quick 16-band FFT spectrum for liquid animated visualizer
                    fft = np.abs(np.fft.rfft(mono.astype(np.float32) / 32768.0))
                    bins = np.array_split(fft[1: min(len(fft), 96)], 16)
                    new_bands = []
                    for i, b in enumerate(bins):
                        val = float(np.mean(b)) * 0.25 if len(b) else 0.0
                        val = min(1.0, max(norm * 0.35, math.pow(max(val, 1e-5), 0.65)))
                        smoothed = self._bands[i] * 0.45 + val * 0.55
                        new_bands.append(round(smoothed, 3))
                    self._bands = new_bands
                    self._on_level(round(norm, 3), list(self._bands))

            try:
                self._stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16",
                    blocksize=1024,
                    device=device_index,
                    callback=callback,
                )
            except Exception:
                # Fallback to system default if specific device ID changed
                self._stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16",
                    blocksize=1024,
                    callback=callback,
                )
            self._recording = True
            self._stream.start()

    def stop(self) -> tuple[bytes, float, bool]:
        """Stop capturing and return (wav_bytes, duration_seconds, has_speech)."""
        with self._lock:
            self._recording = False
            stream = self._stream
            self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        with self._lock:
            chunks = self._chunks
            self._chunks = []
        if not chunks:
            return b"", 0.0, False
        pcm = np.concatenate(chunks, axis=0)
        duration = len(pcm) / float(SAMPLE_RATE)

        # Speech energy gate: ignore accidental short taps and pure background silence
        norm = pcm.astype(np.float32) / 32768.0
        peak_abs = float(np.max(np.abs(norm))) if len(norm) else 0.0
        win = int(SAMPLE_RATE * 0.05)  # 50ms windows
        usable = (len(norm) // win) * win
        if usable >= win:
            frames = norm[:usable].reshape(-1, win)
            frame_rms = np.sqrt(np.mean(frames * frames, axis=1))
            p95_rms = float(np.percentile(frame_rms, 95))
        else:
            p95_rms = float(np.sqrt(np.mean(norm * norm))) if len(norm) else 0.0
        has_speech = (peak_abs >= 0.012) and (p95_rms >= 0.0035)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue(), duration, has_speech
