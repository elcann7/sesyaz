from __future__ import annotations

import ctypes
import io
import math
import os
import struct
import sys
import threading
import time
import uuid
import wave
import winsound
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon

from audio_engine import AudioRecorder, list_input_devices
from config import APP_NAME, DATA_DIR, AppConfig, load_history, save_history
from server import EventBus, start_local_server
from transcriber import LiveTranscribeStreamer, polish_text, transcribe_wav
from win32_io import (
    GlobalHotkeyListener,
    get_foreground_window_info,
    make_window_noactivate,
    set_autostart,
    type_text_into_active_window,
)


if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    EXE_PATH = Path(sys.executable).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent
    EXE_PATH = BASE_DIR / "main.py"

DIST_DIR = BASE_DIR / "ui_dist"
if not DIST_DIR.exists():
    DIST_DIR = Path(sys.executable).resolve().parent / "ui_dist"


def _make_soft_chime_wav(freq_start: float, freq_end: float, dur_ms: int = 75, gain: float = 0.22) -> bytes:
    """Synthesize a soft studio sine blip in memory for non-intrusive feedback."""
    sr = 22050
    n = int(sr * dur_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        phase = 0.0
        for i in range(n):
            t = i / max(1, n - 1)
            freq = freq_start + (freq_end - freq_start) * t
            env = math.sin(math.pi * t) ** 1.4
            phase += 2.0 * math.pi * freq / sr
            val = int(32767 * gain * env * math.sin(phase))
            frames += struct.pack("<h", val)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


CHIME_START = _make_soft_chime_wav(540.0, 780.0, 70, 0.18)
CHIME_DONE = _make_soft_chime_wav(680.0, 960.0, 80, 0.16)
CHIME_ERROR = _make_soft_chime_wav(320.0, 220.0, 110, 0.20)


def _play_chime(wav_data: bytes, enabled: bool) -> None:
    if not enabled:
        return
    try:
        winsound.PlaySound(wav_data, winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass


def _build_tray_icon(recording: bool = False) -> QIcon:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if recording:
        bg_fill = (244, 244, 246, 255)
        bar_fill = (10, 10, 11, 255)
        outline_col = (244, 244, 246, 255)
    else:
        bg_fill = (14, 14, 17, 255)
        bar_fill = (244, 244, 246, 255)
        outline_col = (120, 120, 130, 255)
    draw.rounded_rectangle([4, 4, size - 4, size - 4], radius=18, fill=bg_fill, outline=outline_col, width=3)
    # 5 sound wave bars
    heights = [14, 26, 36, 26, 14] if not recording else [20, 34, 42, 34, 20]
    for idx, h in enumerate(heights):
        x0 = 15 + idx * 8
        y0 = (size - h) // 2
        draw.rounded_rectangle([x0, y0, x0 + 4, y0 + h], radius=2, fill=bar_fill)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    pix = QPixmap()
    pix.loadFromData(bio.getvalue())
    return QIcon(pix)


class UiBridgeSignals(QObject):
    show_pill = Signal()
    hide_pill_delayed = Signal(int)
    show_studio = Signal()
    update_tray = Signal(bool)
    drag_studio = Signal()
    minimize_studio = Signal()
    hide_studio = Signal()
    quit_app = Signal()
    copy_text = Signal(str)


class FramelessWebWindow(QMainWindow):
    def __init__(self, url: str, width: int, height: int, pill_mode: bool = False) -> None:
        super().__init__()
        self.pill_mode = pill_mode
        flags = Qt.WindowType.FramelessWindowHint
        if pill_mode:
            flags |= (
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowDoesNotAcceptFocus
            )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if pill_mode:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.resize(width, height)
        self.view = QWebEngineView(self)
        self.view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        self.view.setUrl(QUrl(url))
        self.setCentralWidget(self.view)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.pill_mode:
            make_window_noactivate(int(self.winId()), click_through=True)


class SesYazApp:
    def __init__(self, start_minimized: bool = False) -> None:
        self.config = AppConfig.load()
        self.history: list[dict] = load_history()
        self.bus = EventBus()
        self.signals = UiBridgeSignals()

        self.status = "idle"  # idle | recording | transcribing | done | error
        self.interim_text = ""
        self.last_text = ""
        self.last_error = ""
        self.last_target_app = ""
        self.last_latency_ms = 0
        self.session_chars = 0
        self._last_record_from_studio = False
        self._lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._pill_hide_timer: QTimer | None = None
        self._live_streamer: LiveTranscribeStreamer | None = None

        self.recorder = AudioRecorder(on_level=self._on_audio_level, on_pcm=self._on_audio_pcm)
        self.hotkeys = GlobalHotkeyListener(
            ptt_key=self.config.ptt_key,
            toggle_hotkey=self.config.toggle_hotkey,
            on_ptt_down=lambda: self.start_recording(from_studio=False),
            on_ptt_up=self.stop_and_transcribe,
            on_toggle=lambda: self.toggle_recording(from_studio=False),
        )

        self.server, self.port = start_local_server(
            dist_dir=DIST_DIR,
            event_bus=self.bus,
            get_state=self.get_state,
            handle_action=self.handle_action,
        )
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "server.port").write_text(str(self.port), encoding="utf-8")
        except OSError:
            pass

        # Apply Windows autostart setting cleanly on startup
        self._sync_autostart()

        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setWindowIcon(_build_tray_icon(False))

        base_url = f"http://127.0.0.1:{self.port}/"
        self.studio_win = FramelessWebWindow(f"{base_url}?view=studio", 1040, 700, pill_mode=False)
        self.pill_win = FramelessWebWindow(f"{base_url}?view=pill", 460, 128, pill_mode=True)
        self._position_pill()
        self._center_studio()

        # System Tray
        self.icon_idle = _build_tray_icon(False)
        self.icon_rec = _build_tray_icon(True)
        self.tray = QSystemTrayIcon(self.icon_idle, self.qt_app)
        self.tray.setToolTip("SesYaz — Live Voice Dictation (AZ + Tech)")
        menu = QMenu()
        act_open = QAction("Open Studio", self.qt_app)
        act_open.triggered.connect(self._slot_show_studio)
        act_toggle = QAction("Start / Stop Dictation", self.qt_app)
        act_toggle.triggered.connect(lambda: threading.Thread(target=self.toggle_recording, daemon=True).start())
        act_quit = QAction("Quit", self.qt_app)
        act_quit.triggered.connect(self._slot_quit)
        menu.addAction(act_open)
        menu.addAction(act_toggle)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # Connect thread-safe Qt UI signals
        self.signals.show_pill.connect(self._slot_show_pill)
        self.signals.hide_pill_delayed.connect(self._slot_hide_pill_delayed)
        self.signals.show_studio.connect(self._slot_show_studio)
        self.signals.update_tray.connect(self._slot_update_tray)
        self.signals.drag_studio.connect(self._slot_drag_studio)
        self.signals.minimize_studio.connect(self.studio_win.showMinimized)
        self.signals.hide_studio.connect(self.studio_win.hide)
        self.signals.quit_app.connect(self._slot_quit)
        self.signals.copy_text.connect(lambda t: self.qt_app.clipboard().setText(t))

        # Single-instance wake listener (Windows Named Event)
        self._wake_event = ctypes.windll.kernel32.CreateEventW(None, False, False, "Local\\SesYazShowStudioEvent")
        threading.Thread(target=self._watch_wake_event, daemon=True).start()

        self.hotkeys.start()
        # Keep Pill WebEngine window GPU-warm, invisible, and click-through so first press is instant
        self.pill_win.setWindowOpacity(0.0)
        self.pill_win.show()
        make_window_noactivate(int(self.pill_win.winId()), click_through=True)
        if not start_minimized:
            self.studio_win.show()

    def _watch_wake_event(self) -> None:
        while self._wake_event:
            res = ctypes.windll.kernel32.WaitForSingleObject(self._wake_event, 1000)
            if res == 0:
                self.signals.show_studio.emit()

    def _position_pill(self) -> None:
        screen = self.qt_app.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.pill_win.width()) // 2
        if self.config.pill_position == "top":
            y = screen.y() + 18
        else:
            y = screen.y() + screen.height() - self.pill_win.height() - 18
        self.pill_win.move(x, y)

    def _center_studio(self) -> None:
        screen = self.qt_app.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.studio_win.width()) // 2
        y = screen.y() + (screen.height() - self.studio_win.height()) // 2
        self.studio_win.move(x, y)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._slot_show_studio()

    def _slot_show_pill(self) -> None:
        if self._pill_hide_timer:
            self._pill_hide_timer.stop()
        self._position_pill()
        self.pill_win.setWindowOpacity(1.0)
        if not self.pill_win.isVisible():
            self.pill_win.show()
        self.pill_win.raise_()
        make_window_noactivate(int(self.pill_win.winId()), click_through=True)

    def _slot_hide_pill_delayed(self, ms: int) -> None:
        if self._pill_hide_timer:
            self._pill_hide_timer.stop()
        if ms <= 0:
            self.pill_win.setWindowOpacity(0.0)
            return
        self._pill_hide_timer = QTimer(self.qt_app)
        self._pill_hide_timer.setSingleShot(True)
        self._pill_hide_timer.timeout.connect(lambda: self.pill_win.setWindowOpacity(0.0))
        self._pill_hide_timer.start(ms)

    def _slot_show_studio(self) -> None:
        self.studio_win.showNormal()
        self.studio_win.raise_()
        self.studio_win.activateWindow()

    def _slot_update_tray(self, rec: bool) -> None:
        self.tray.setIcon(self.icon_rec if rec else self.icon_idle)

    def _slot_drag_studio(self) -> None:
        handle = self.studio_win.windowHandle()
        if handle:
            handle.startSystemMove()

    def _slot_quit(self) -> None:
        self.hotkeys.stop()
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.tray.hide()
        self.qt_app.quit()

    def _sync_autostart(self) -> None:
        if getattr(sys, "frozen", False):
            cmd = f'"{EXE_PATH}" --minimized'
        else:
            launcher = BASE_DIR.parent / "SesYaz.vbs"
            if launcher.exists():
                cmd = f'wscript.exe "{launcher}" --minimized'
            else:
                pyw = Path(sys.executable).with_name("pythonw.exe")
                exe = pyw if pyw.exists() else Path(sys.executable)
                cmd = f'"{exe}" "{BASE_DIR / "main.py"}" --minimized'
        set_autostart(self.config.autostart, cmd)

    def _on_audio_level(self, rms: float, bands: list[float]) -> None:
        self.bus.publish("level", {"rms": rms, "bands": bands})

    def _on_audio_pcm(self, pcm_bytes: bytes) -> None:
        streamer = self._live_streamer
        if streamer is not None:
            streamer.push_pcm(pcm_bytes)

    def _on_live_interim(self, text: str) -> None:
        self.interim_text = text
        self._publish_status()

    def _masked_config(self) -> dict:
        d = asdict(self.config)
        keys = d.pop("api_keys", [])
        d["apiKeyCount"] = len(keys)
        d["apiKeyPreviews"] = [f"{k[:6]}••••{k[-4:]}" if len(k) > 10 else "••••" for k in keys]
        return d

    def get_state(self) -> dict:
        total_words = sum(len(str(item.get("text", "")).split()) for item in self.history)
        return {
            "status": self.status,
            "lastText": self.last_text,
            "lastError": self.last_error,
            "lastTargetApp": self.last_target_app,
            "lastLatencyMs": self.last_latency_ms,
            "totalTranscriptions": len(self.history),
            "totalWords": total_words,
            "minutesSaved": round(total_words / 42.0, 1),
            "config": self._masked_config(),
            "devices": list_input_devices(),
            "history": self.history[:80],
        }

    def _publish_status(self) -> None:
        self.bus.publish("status", {
            "status": self.status,
            "interimText": self.interim_text,
            "lastText": self.last_text,
            "lastError": self.last_error,
            "lastTargetApp": self.last_target_app,
            "lastLatencyMs": self.last_latency_ms,
        })

    def start_recording(self, from_studio: bool = False) -> None:
        with self._lock:
            if self.status in ("recording", "transcribing"):
                return
            _, title = get_foreground_window_info()
            self._last_record_from_studio = from_studio
            self.last_target_app = "" if from_studio else (title or "Active Window")
            self.last_error = ""
            self.interim_text = ""
            self.status = "recording"

        # Show Pill HUD, chime, and UI status IMMEDIATELY before audio driver initialization
        _play_chime(CHIME_START, self.config.sound_cue)
        self.signals.update_tray.emit(True)
        if not from_studio:
            self.signals.show_pill.emit()
        self._publish_status()

        try:
            with self._stream_lock:
                # Re-check in case release happened while waiting for stream lock
                if self.status != "recording":
                    return
                streamer = LiveTranscribeStreamer(
                    api_keys=self.config.api_keys,
                    language_mode=self.config.language_mode,
                    custom_vocabulary=self.config.custom_vocabulary,
                    transcription_mode=self.config.transcription_mode,
                    on_interim=self._on_live_interim,
                )
                self._live_streamer = streamer
                streamer.start()
                self.recorder.start(device_index=self.config.device_index)
        except Exception as exc:
            if self._live_streamer:
                self._live_streamer.abort()
                self._live_streamer = None
            self.signals.update_tray.emit(False)
            with self._lock:
                self.status = "error"
                self.last_error = f"Microphone error: {exc}"
            _play_chime(CHIME_ERROR, self.config.sound_cue)
            self._publish_status()
            if not from_studio:
                self.signals.show_pill.emit()
                self.signals.hide_pill_delayed.emit(2400)

    def stop_and_transcribe(self) -> None:
        with self._stream_lock:
            with self._lock:
                if self.status != "recording":
                    return
                from_studio = self._last_record_from_studio
                target_app = self.last_target_app
                streamer = self._live_streamer
                self._live_streamer = None
            wav_bytes, dur, has_speech = self.recorder.stop()
        self.signals.update_tray.emit(False)

        # Ignore accidental quick taps (<0.35s) or empty/silent clips before committing
        if dur < 0.35 or not wav_bytes or not has_speech:
            if streamer:
                streamer.abort()
            with self._lock:
                self.status = "idle"
                self.interim_text = ""
            self._publish_status()
            if not from_studio:
                self.signals.hide_pill_delayed.emit(0)
            return

        with self._lock:
            self.status = "transcribing"
        self._publish_status()

        try:
            res = None
            live_connected = False
            if streamer is not None:
                try:
                    res = streamer.finish(timeout_s=4.2)
                    live_connected = streamer.connected_ok
                    if res.text.strip() and self.config.dictation_mode == "polish" and self.config.transcription_mode != "verbatim":
                        polished = polish_text(
                            res.text,
                            self.config.api_keys,
                            self.config.language_mode,
                            self.config.custom_vocabulary,
                        )
                        if polished:
                            res.text = polished
                            res.model = "gemini-3.5-transcribe-live + flash-lite"
                            res.mode = "polish"
                except Exception:
                    res = None

            # Only invoke batch fallback when Live WebSocket itself failed to connect
            if (res is None or not res.text.strip()) and not live_connected:
                res = transcribe_wav(
                    wav_bytes=wav_bytes,
                    api_keys=self.config.api_keys[:2],
                    dictation_mode=self.config.dictation_mode,
                    language_mode=self.config.language_mode,
                    custom_vocabulary=self.config.custom_vocabulary,
                    transcription_mode=self.config.transcription_mode,
                )
            text = res.text.strip() if res else ""
            if not text:
                with self._lock:
                    self.status = "idle"
                    self.interim_text = ""
                self._publish_status()
                if not from_studio:
                    self.signals.hide_pill_delayed.emit(0)
                return

            if not from_studio:
                # Directly inject into active cursor without manual copy-paste
                type_text_into_active_window(
                    text + " ",
                    mode=self.config.typing_mode,
                    auto_enter=self.config.auto_enter,
                )

            entry = {
                "id": str(uuid.uuid4())[:8],
                "text": text,
                "model": res.model,
                "mode": res.mode,
                "latencyMs": res.latency_ms,
                "durationSec": round(dur, 1),
                "targetApp": target_app or "SesYaz Studio",
                "createdAt": int(time.time() * 1000),
            }
            self.history.insert(0, entry)
            save_history(self.history)

            with self._lock:
                self.interim_text = ""
                self.last_text = text
                self.last_latency_ms = res.latency_ms
                self.last_error = ""
                self.status = "done"

            _play_chime(CHIME_DONE, self.config.sound_cue)
            self._publish_status()
            self.bus.publish("history", self.get_state())

            def reset_idle() -> None:
                with self._lock:
                    if self.status in ("done", "error"):
                        self.status = "idle"
                self._publish_status()

            if not from_studio:
                self.signals.hide_pill_delayed.emit(1300)
                threading.Timer(1.35, reset_idle).start()
            else:
                threading.Timer(1.4, reset_idle).start()
        except Exception as exc:
            with self._lock:
                self.interim_text = ""
                self.status = "error"
                self.last_error = str(exc)
            _play_chime(CHIME_ERROR, self.config.sound_cue)
            self._publish_status()

            def reset_err() -> None:
                with self._lock:
                    if self.status == "error":
                        self.status = "idle"
                self._publish_status()

            if not from_studio:
                self.signals.hide_pill_delayed.emit(3000)
            threading.Timer(3.1, reset_err).start()

    def toggle_recording(self, from_studio: bool = False) -> None:
        if self.status == "recording":
            self.stop_and_transcribe()
        elif self.status in ("idle", "done", "error"):
            self.start_recording(from_studio=from_studio)

    def handle_action(self, path: str, body: dict[str, Any]) -> tuple[int, dict]:
        if path == "/api/record/toggle":
            from_studio = bool(body.get("fromStudio", True))
            threading.Thread(target=self.toggle_recording, args=(from_studio,), daemon=True).start()
            return 200, {"ok": True}

        if path == "/api/record/start":
            from_studio = bool(body.get("fromStudio", True))
            threading.Thread(target=self.start_recording, args=(from_studio,), daemon=True).start()
            return 200, {"ok": True}

        if path == "/api/record/stop":
            threading.Thread(target=self.stop_and_transcribe, daemon=True).start()
            return 200, {"ok": True}

        if path == "/api/config":
            for k in (
                "ptt_key",
                "toggle_hotkey",
                "dictation_mode",
                "transcription_mode",
                "language_mode",
                "typing_mode",
                "auto_enter",
                "device_index",
                "autostart",
                "sound_cue",
                "pill_position",
                "custom_vocabulary",
            ):
                if k in body:
                    setattr(self.config, k, body[k])
            if body.get("transcription_mode") == "verbatim" and "dictation_mode" not in body:
                self.config.dictation_mode = "accurate"
            elif body.get("dictation_mode") == "polish" and "transcription_mode" not in body:
                self.config.transcription_mode = "smart"
            if body.get("add_api_key"):
                new_k = str(body["add_api_key"]).strip()
                if new_k and new_k not in self.config.api_keys:
                    self.config.api_keys.insert(0, new_k)
            if isinstance(body.get("remove_api_key_index"), int):
                idx = body["remove_api_key_index"]
                if 0 <= idx < len(self.config.api_keys) and len(self.config.api_keys) > 1:
                    self.config.api_keys.pop(idx)
            self.config.save()
            self.hotkeys.update_bindings(self.config.ptt_key, self.config.toggle_hotkey)
            self._sync_autostart()
            self._position_pill()
            self.bus.publish("history", self.get_state())
            return 200, self.get_state()

        if path == "/api/hotkey/capture":
            target_field = str(body.get("field", "toggle_hotkey"))
            def on_captured(key_str: str) -> None:
                if target_field in ("ptt_key", "toggle_hotkey"):
                    setattr(self.config, target_field, key_str)
                    self.config.save()
                    self.hotkeys.update_bindings(self.config.ptt_key, self.config.toggle_hotkey)
                self.bus.publish("hotkey_captured", {"field": target_field, "value": key_str})
                self.bus.publish("history", self.get_state())
            self.hotkeys.start_capture(on_captured)
            return 200, {"ok": True}

        if path == "/api/hotkey/cancel":
            self.hotkeys.cancel_capture()
            return 200, {"ok": True}

        if path == "/api/history/clear":
            self.history = []
            save_history(self.history)
            self.bus.publish("history", self.get_state())
            return 200, self.get_state()

        if path == "/api/history/delete":
            hid = body.get("id")
            self.history = [h for h in self.history if h.get("id") != hid]
            save_history(self.history)
            self.bus.publish("history", self.get_state())
            return 200, self.get_state()

        if path == "/api/window/drag":
            self.signals.drag_studio.emit()
            return 200, {"ok": True}

        if path == "/api/window/minimize":
            self.signals.minimize_studio.emit()
            return 200, {"ok": True}

        if path == "/api/window/hide":
            self.signals.hide_studio.emit()
            return 200, {"ok": True}

        if path == "/api/window/quit":
            self.signals.quit_app.emit()
            return 200, {"ok": True}

        if path == "/api/clipboard/copy":
            txt = str(body.get("text", ""))
            if txt:
                self.signals.copy_text.emit(txt)
            return 200, {"ok": True}

        return 404, {"error": "Unknown endpoint"}

    def run(self) -> int:
        return self.qt_app.exec()


def _wake_existing_instance() -> bool:
    handle = ctypes.windll.kernel32.OpenEventW(0x0002, False, "Local\\SesYazShowStudioEvent")
    if handle:
        ctypes.windll.kernel32.SetEvent(handle)
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


if __name__ == "__main__":
    minimized = "--minimized" in sys.argv
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\SesYazSingleInstanceMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        if not minimized:
            _wake_existing_instance()
        sys.exit(0)

    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox --enable-webgl")
    app = SesYazApp(start_minimized=minimized)
    sys.exit(app.run())
