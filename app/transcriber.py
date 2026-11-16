from __future__ import annotations

import asyncio
import base64
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from google import genai
from google.genai import types


@dataclass
class TranscriptionResult:
    text: str
    model: str
    latency_ms: int
    mode: str


def _build_polish_instruction(language_mode: str, vocabulary: List[str]) -> str:
    vocab_hint = ", ".join(vocabulary[:35]) if vocabulary else "Claude Code, Git, API"
    lang_note = {
        "az-tech": "natural Azerbaijani speech mixed with English technical terms",
        "az": "standard Azerbaijani orthography (ə, ş, ğ, ç, ö, ü, ı)",
        "en": "clear natural English",
        "auto": "the exact language spoken by the speaker",
    }.get(language_mode, "natural Azerbaijani")

    return (
        "You clean up raw voice dictation before injecting it directly at the active cursor "
        f"(terminal, IDE, or chat). Language: {lang_note}.\n"
        f"Custom technical vocabulary (spell accurately): {vocab_hint}.\n"
        "Rules:\n"
        "1. Return ONLY plain text — no explanations, quotes, backticks (`), asterisks (*), or Markdown formatting.\n"
        "2. Remove filler words and fix punctuation lightly, while preserving meaning, word order, and technical identifiers.\n"
        "3. If there is no clear speech or the input is empty, return ONLY an empty string — never invent sentences from the vocabulary list."
    )


def _language_codes_for(language_mode: str) -> List[str]:
    if language_mode == "az":
        return ["az"]
    if language_mode == "en":
        return ["en"]
    if language_mode == "auto":
        return []
    return ["az", "en"]


def polish_text(
    raw_text: str,
    api_keys: List[str],
    language_mode: str = "az-tech",
    custom_vocabulary: List[str] | None = None,
) -> str:
    """Quickly polish already-transcribed speech with gemini-3.5-flash-lite."""
    raw = (raw_text or "").strip()
    if not raw:
        return ""
    vocab = custom_vocabulary or []
    prompt = _build_polish_instruction(language_mode, vocab)
    for key in api_keys:
        k = (key or "").strip()
        if not k:
            continue
        try:
            client_v1 = genai.Client(api_key=k)
            polished = client_v1.interactions.create(
                model="gemini-3.5-flash-lite",
                system_instruction=prompt,
                input=[{"type": "text", "text": f"Clean up this raw transcript following the rules:\n{raw}"}],
                store=False,
            )
            clean = (polished.output_text or "").strip().strip("`")
            return clean or raw
        except Exception:
            continue
    return raw


class LiveTranscribeStreamer:
    """Real-time streaming STT via gemini-3.5-transcribe-live (Unlimited Live API WebSocket)."""

    def __init__(
        self,
        api_keys: List[str],
        language_mode: str = "az-tech",
        custom_vocabulary: List[str] | None = None,
        on_interim: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.api_keys = [k.strip() for k in api_keys if k and k.strip()]
        self.language_mode = language_mode
        self.vocabulary = list(custom_vocabulary or [])
        self.on_interim = on_interim

        self._pcm_queue: queue.SimpleQueue[Optional[bytes]] = queue.SimpleQueue()
        self._done_event = threading.Event()
        self._aborted = False
        self._connected_ok = False
        self._end_sent = threading.Event()
        self._final_segments: List[str] = []
        self._latest_interim = ""
        self._error: Optional[Exception] = None
        self._thread: Optional[threading.Thread] = None
        self._t_start = 0.0
        self._t_finish = 0.0

    @property
    def connected_ok(self) -> bool:
        return self._connected_ok

    def start(self) -> None:
        if not self.api_keys:
            return
        self._t_start = time.perf_counter()
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def push_pcm(self, pcm_bytes: bytes) -> None:
        if pcm_bytes and not self._aborted and not self._end_sent.is_set():
            self._pcm_queue.put(pcm_bytes)

    def abort(self) -> None:
        self._aborted = True
        self._pcm_queue.put(None)

    def finish(self, timeout_s: float = 4.2) -> TranscriptionResult:
        """Signal speech end, flush queued audio, and return finalized live transcript."""
        self._t_finish = time.perf_counter()
        self._pcm_queue.put(None)
        self._done_event.wait(timeout=timeout_s)
        latency_ms = int((time.perf_counter() - (self._t_finish or time.perf_counter())) * 1000)

        if self._error is not None and not self._final_segments and not self._latest_interim:
            raise self._error

        text = " ".join(s.strip() for s in self._final_segments if s and s.strip()).strip()
        if not text and self._latest_interim:
            text = self._latest_interim.strip()
        return TranscriptionResult(
            text=text,
            model="gemini-3.5-transcribe-live",
            latency_ms=max(1, latency_ms),
            mode="live",
        )

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._async_session())
        except Exception as exc:
            self._error = exc
        finally:
            self._done_event.set()

    async def _async_session(self) -> None:
        codes = _language_codes_for(self.language_mode)
        t_cfg = types.AudioTranscriptionConfig(
            mode="SMART",
            language_codes=codes,
            custom_vocabulary=self.vocabulary[:50] if self.vocabulary else None,
        )
        live_cfg = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
            ),
            input_audio_transcription=t_cfg,
        )

        last_err: Optional[Exception] = None
        for key in self.api_keys:
            if self._aborted:
                return
            try:
                client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
                async with client.aio.live.connect(
                    model="gemini-3.5-transcribe-live",
                    config=live_cfg,
                ) as session:
                    if self._aborted:
                        return
                    self._connected_ok = True
                    await session.send_realtime_input(activity_start=types.ActivityStart())

                    finished_sending = asyncio.Event()
                    received_after_end = asyncio.Event()

                    async def sender() -> None:
                        buf = bytearray()
                        while not self._aborted:
                            drained_end = False
                            while True:
                                try:
                                    item = self._pcm_queue.get_nowait()
                                    if item is None:
                                        drained_end = True
                                        break
                                    buf.extend(item)
                                except queue.Empty:
                                    break
                            if buf and not self._aborted:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=bytes(buf), mime_type="audio/pcm;rate=16000")
                                )
                                buf.clear()
                            if drained_end or self._aborted:
                                break
                            await asyncio.sleep(0.03)

                        if not self._aborted:
                            self._end_sent.set()
                            await session.send_realtime_input(activity_end=types.ActivityEnd())
                            finished_sending.set()

                    async def receiver() -> None:
                        async for resp in session.receive():
                            if self._aborted:
                                break
                            sc = getattr(resp, "server_content", None)
                            if not sc:
                                continue
                            interim = getattr(sc, "interim_input_transcription", None)
                            if interim and getattr(interim, "text", None):
                                txt = interim.text.strip()
                                if txt and txt != self._latest_interim:
                                    self._latest_interim = txt
                                    if self.on_interim:
                                        try:
                                            committed = " ".join(self._final_segments).strip()
                                            preview = f"{committed} {txt}".strip() if committed else txt
                                            self.on_interim(preview)
                                        except Exception:
                                            pass
                            final_tr = getattr(sc, "input_transcription", None)
                            if final_tr and getattr(final_tr, "text", None):
                                seg = final_tr.text.strip()
                                if seg:
                                    self._final_segments.append(seg)
                                    self._latest_interim = ""
                                if finished_sending.is_set():
                                    received_after_end.set()
                                    break
                            if getattr(sc, "turn_complete", False) and finished_sending.is_set():
                                received_after_end.set()
                                break

                    send_task = asyncio.create_task(sender())
                    recv_task = asyncio.create_task(receiver())
                    await send_task
                    if not self._aborted:
                        wait_s = 1.6 if self._final_segments else 2.6
                        try:
                            await asyncio.wait_for(received_after_end.wait(), timeout=wait_s)
                        except asyncio.TimeoutError:
                            pass
                    recv_task.cancel()
                    try:
                        await recv_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    return
            except Exception as err:
                last_err = err
                continue

        if last_err is not None:
            self._error = last_err


def transcribe_wav(
    wav_bytes: bytes,
    api_keys: List[str],
    dictation_mode: str = "accurate",
    language_mode: str = "az-tech",
    custom_vocabulary: List[str] | None = None,
) -> TranscriptionResult:
    """Fallback batch transcription via Gemini Interactions API with multi-key failover."""
    if not wav_bytes:
        return TranscriptionResult(text="", model="none", latency_ms=0, mode=dictation_mode)

    keys = [k.strip() for k in api_keys if k and k.strip()]
    if not keys:
        raise RuntimeError("No Gemini API key configured. Add one in Settings.")

    wav_b64 = base64.b64encode(wav_bytes).decode("ascii")
    vocab = custom_vocabulary or []
    t0 = time.perf_counter()
    last_err: Exception | None = None

    for key in keys:
        try:
            client_beta = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
            t_cfg: dict = {"mode": "smart"}
            codes = _language_codes_for(language_mode)
            if codes:
                t_cfg["language_codes"] = codes
            if vocab:
                t_cfg["custom_vocabulary"] = vocab[:50]
            interaction = client_beta.interactions.create(
                model="gemini-3.5-transcribe",
                input=[{"type": "audio", "data": wav_b64, "mime_type": "audio/wav"}],
                generation_config={"transcription_config": t_cfg},
                store=False,
            )
            raw_txt = (interaction.output_text or "").strip()
            if not raw_txt or raw_txt in ("00:00", '""', "''"):
                return TranscriptionResult(
                    text="",
                    model="gemini-3.5-transcribe",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    mode=dictation_mode,
                )

            if dictation_mode != "polish":
                return TranscriptionResult(
                    text=raw_txt,
                    model="gemini-3.5-transcribe",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    mode="accurate",
                )

            clean_txt = polish_text(raw_txt, keys, language_mode, vocab)
            return TranscriptionResult(
                text=clean_txt,
                model="gemini-3.5-transcribe + flash-lite",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                mode="polish",
            )
        except Exception as err:
            last_err = err

    for key in keys:
        try:
            client_v1 = genai.Client(api_key=key)
            prompt = _build_polish_instruction(language_mode, vocab)
            interaction = client_v1.interactions.create(
                model="gemini-3.5-flash-lite",
                system_instruction=prompt,
                input=[
                    {"type": "audio", "data": wav_b64, "mime_type": "audio/wav"},
                    {"type": "text", "text": "Transcribe the speech in this audio verbatim. If there is no speech, return an empty string."},
                ],
                store=False,
            )
            txt = (interaction.output_text or "").strip().strip("`")
            if txt in ("00:00", '""', "''"):
                txt = ""
            return TranscriptionResult(
                text=txt,
                model="gemini-3.5-flash-lite",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                mode=dictation_mode,
            )
        except Exception as err:
            last_err = err
            continue

    raise RuntimeError(f"Gemini API error: {last_err}")
