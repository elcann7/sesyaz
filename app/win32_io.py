from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import threading
import time
import winreg
from typing import Callable, Optional, Set

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
LLKHF_INJECTED = 0x00000010

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_RETURN = 0x0D
VK_V = 0x56

MODIFIER_VKS = {
    VK_SHIFT,
    VK_CONTROL,
    VK_MENU,
    VK_LSHIFT,
    VK_RSHIFT,
    VK_LCONTROL,
    VK_RCONTROL,
    VK_LMENU,
    VK_RMENU,
    0x5B,  # LWIN
    0x5C,  # RWIN
}

KEY_NAME_TO_VK = {
    "rctrl": VK_RCONTROL,
    "lctrl": VK_LCONTROL,
    "ralt": VK_RMENU,
    "lalt": VK_LMENU,
    "rshift": VK_RSHIFT,
    "lshift": VK_LSHIFT,
    "space": 0x20,
    "tab": 0x09,
    "capslock": 0x14,
    "insert": 0x2D,
    "pause": 0x13,
    "`": 0xC0,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}
for _c in "abcdefghijklmnopqrstuvwxyz":
    KEY_NAME_TO_VK[_c] = ord(_c.upper())
for _d in "0123456789":
    KEY_NAME_TO_VK[_d] = ord(_d)

VK_TO_NAME = {v: k for k, v in KEY_NAME_TO_VK.items()}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wt.DWORD),
        ("scanCode", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wt.DWORD), ("union", _INPUTunion)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wt.WPARAM, wt.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.UnhookWindowsHookEx.restype = wt.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = wt.BOOL
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wt.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wt.SHORT

kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wt.HGLOBAL
kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
kernel32.GlobalUnlock.restype = wt.BOOL
kernel32.GlobalFree.argtypes = [wt.HGLOBAL]
kernel32.GlobalFree.restype = wt.HGLOBAL

user32.OpenClipboard.argtypes = [wt.HWND]
user32.OpenClipboard.restype = wt.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wt.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wt.BOOL
user32.GetClipboardData.argtypes = [wt.UINT]
user32.GetClipboardData.restype = wt.HANDLE
user32.SetClipboardData.argtypes = [wt.UINT, wt.HANDLE]
user32.SetClipboardData.restype = wt.HANDLE


def make_window_noactivate(hwnd: int, click_through: bool = False) -> None:
    """Apply WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW so overlay pill never steals focus."""
    if not hwnd:
        return
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    flags = WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | (WS_EX_TRANSPARENT if click_through else 0)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | flags)


def get_foreground_window_info() -> tuple[int, str]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0, ""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return int(hwnd), buf.value


def set_autostart(enabled: bool, script_cmd: str) -> bool:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "SesYaz", 0, winreg.REG_SZ, script_cmd)
            else:
                try:
                    winreg.DeleteValue(key, "SesYaz")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def _send_inputs(inputs: list[INPUT]) -> None:
    if not inputs:
        return
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _release_pressed_modifiers() -> None:
    """Release physical Ctrl/Alt/Shift keys before injecting text so shortcuts don't misfire."""
    ups: list[INPUT] = []
    for vk in (VK_LCONTROL, VK_RCONTROL, VK_CONTROL, VK_LMENU, VK_RMENU, VK_MENU, VK_LSHIFT, VK_RSHIFT, VK_SHIFT):
        if user32.GetAsyncKeyState(vk) & 0x8000:
            flags = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if vk in (VK_RCONTROL, VK_RMENU) else 0)
            ups.append(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags)))
    if ups:
        _send_inputs(ups)
        time.sleep(0.025)


def _send_vk(vk: int, key_up: bool = False) -> INPUT:
    flags = (KEYEVENTF_KEYUP if key_up else 0) | (
        KEYEVENTF_EXTENDEDKEY if vk in (VK_RCONTROL, VK_RMENU) else 0
    )
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags))


def send_unicode_text(text: str, auto_enter: bool = False) -> None:
    """Type Unicode text directly into active window via SendInput KEYEVENTF_UNICODE."""
    if not text:
        return
    _release_pressed_modifiers()
    normalized = text.replace("\r\n", "\n")
    batch: list[INPUT] = []

    def flush() -> None:
        nonlocal batch
        if batch:
            _send_inputs(batch)
            batch = []
            time.sleep(0.004)

    for ch in normalized:
        if ch == "\n":
            # Use Shift+Return for inline newlines so chat apps/Claude Code don't submit mid-prompt
            batch.append(_send_vk(VK_LSHIFT, False))
            batch.append(_send_vk(VK_RETURN, False))
            batch.append(_send_vk(VK_RETURN, True))
            batch.append(_send_vk(VK_LSHIFT, True))
            flush()
            continue

        utf16_bytes = ch.encode("utf-16-le")
        for i in range(0, len(utf16_bytes), 2):
            code_unit = int.from_bytes(utf16_bytes[i : i + 2], "little")
            batch.append(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=code_unit, dwFlags=KEYEVENTF_UNICODE)))
            batch.append(
                INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(wVk=0, wScan=code_unit, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
                )
            )
        if len(batch) >= 64:
            flush()

    if auto_enter:
        batch.append(_send_vk(VK_RETURN, False))
        batch.append(_send_vk(VK_RETURN, True))

    flush()


def _get_clipboard_text() -> Optional[str]:
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _set_clipboard_text(text: str) -> bool:
    for _ in range(6):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.015)
    else:
        return False

    try:
        user32.EmptyClipboard()
        encoded = (text + "\0").encode("utf-16-le")
        hglob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not hglob:
            return False
        ptr = kernel32.GlobalLock(hglob)
        if not ptr:
            kernel32.GlobalFree(hglob)
            return False
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(hglob)
        if not user32.SetClipboardData(CF_UNICODETEXT, hglob):
            kernel32.GlobalFree(hglob)
            return False
        return True
    finally:
        user32.CloseClipboard()


def paste_text_preserving_clipboard(text: str, auto_enter: bool = False) -> None:
    """Paste long Unicode text cleanly via Ctrl+V and restore user's previous clipboard."""
    if not text:
        return
    prev = _get_clipboard_text()
    if not _set_clipboard_text(text):
        send_unicode_text(text, auto_enter=auto_enter)
        return
    try:
        _release_pressed_modifiers()
        _send_inputs(
            [
                _send_vk(VK_LCONTROL, False),
                _send_vk(VK_V, False),
                _send_vk(VK_V, True),
                _send_vk(VK_LCONTROL, True),
            ]
        )
        time.sleep(0.14)
        if auto_enter:
            _send_inputs([_send_vk(VK_RETURN, False), _send_vk(VK_RETURN, True)])
    finally:
        if prev is not None:
            threading.Timer(0.35, lambda: _set_clipboard_text(prev)).start()


def type_text_into_active_window(text: str, mode: str = "smart", auto_enter: bool = False) -> None:
    if not text:
        return
    if mode == "unicode":
        send_unicode_text(text, auto_enter=auto_enter)
    elif mode == "paste":
        paste_text_preserving_clipboard(text, auto_enter=auto_enter)
    else:
        # "smart": pure zero-clipboard keystrokes for concise dictation, fast paste+restore for huge paragraphs
        if len(text) <= 140 and "\n" not in text:
            send_unicode_text(text, auto_enter=auto_enter)
        else:
            paste_text_preserving_clipboard(text, auto_enter=auto_enter)


def parse_hotkey_combo(combo: str) -> tuple[Set[str], int]:
    """Parse 'ctrl+shift+space' into (modifier_groups, main_vk)."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    mods: Set[str] = set()
    main_vk = 0
    for p in parts:
        if p in ("ctrl", "control"):
            mods.add("ctrl")
        elif p in ("shift",):
            mods.add("shift")
        elif p in ("alt", "menu"):
            mods.add("alt")
        else:
            main_vk = KEY_NAME_TO_VK.get(p, 0)
    return mods, main_vk


class GlobalHotkeyListener:
    """Low-level Windows keyboard hook supporting both Push-to-Talk and Toggle hotkeys."""

    def __init__(
        self,
        ptt_key: str,
        toggle_hotkey: str,
        on_ptt_down: Callable[[], None],
        on_ptt_up: Callable[[], None],
        on_toggle: Callable[[], None],
    ) -> None:
        self.on_ptt_down = on_ptt_down
        self.on_ptt_up = on_ptt_up
        self.on_toggle = on_toggle
        self.ptt_vk = KEY_NAME_TO_VK.get(ptt_key.lower(), VK_RCONTROL)
        self.toggle_mods, self.toggle_vk = parse_hotkey_combo(toggle_hotkey)
        self._ptt_active = False
        self._capture_cb: Optional[Callable[[str], None]] = None
        self._pressed_mods: Set[str] = set()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: int = 0
        self._hook: wt.HHOOK | None = None
        self._proc = None

    def update_bindings(self, ptt_key: str, toggle_hotkey: str) -> None:
        self.ptt_vk = KEY_NAME_TO_VK.get(ptt_key.lower(), VK_RCONTROL)
        self.toggle_mods, self.toggle_vk = parse_hotkey_combo(toggle_hotkey)

    def start_capture(self, cb: Callable[[str], None]) -> None:
        self._capture_cb = cb

    def cancel_capture(self) -> None:
        self._capture_cb = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        ready = threading.Event()

        def runner() -> None:
            self._thread_id = kernel32.GetCurrentThreadId()

            def hook_proc(nCode: int, wParam: int, lParam: int) -> int:
                if nCode >= 0:
                    kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    # Ignore synthetic events from SendInput so auto-typing never re-triggers hotkeys
                    if kb.flags & LLKHF_INJECTED:
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    vk = int(kb.vkCode)
                    is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)

                    if vk in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL):
                        if is_down:
                            self._pressed_mods.add("ctrl")
                        elif is_up:
                            self._pressed_mods.discard("ctrl")
                    elif vk in (VK_SHIFT, VK_LSHIFT, VK_RSHIFT):
                        if is_down:
                            self._pressed_mods.add("shift")
                        elif is_up:
                            self._pressed_mods.discard("shift")
                    elif vk in (VK_MENU, VK_LMENU, VK_RMENU):
                        if is_down:
                            self._pressed_mods.add("alt")
                        elif is_up:
                            self._pressed_mods.discard("alt")

                    # One-shot hotkey capture mode for Settings
                    if self._capture_cb is not None and is_down:
                        key_name = VK_TO_NAME.get(vk)
                        if key_name:
                            cb = self._capture_cb
                            if vk in MODIFIER_VKS and key_name in ("rctrl", "lctrl", "ralt", "lalt", "rshift", "lshift"):
                                self._capture_cb = None
                                threading.Thread(target=cb, args=(key_name,), daemon=True).start()
                                return 1
                            elif vk not in MODIFIER_VKS:
                                parts = sorted(self._pressed_mods) + [key_name]
                                combo = "+".join(parts)
                                self._capture_cb = None
                                threading.Thread(target=cb, args=(combo,), daemon=True).start()
                                return 1

                    # Toggle combo check
                    if (
                        is_down
                        and self.toggle_vk
                        and vk == self.toggle_vk
                        and self.toggle_mods.issubset(self._pressed_mods)
                    ):
                        threading.Thread(target=self.on_toggle, daemon=True).start()
                        return 1

                    # Push-to-Talk single key check
                    if self.ptt_vk and vk == self.ptt_vk:
                        if is_down and not self._ptt_active:
                            self._ptt_active = True
                            threading.Thread(target=self.on_ptt_down, daemon=True).start()
                        elif is_up and self._ptt_active:
                            self._ptt_active = False
                            threading.Thread(target=self.on_ptt_up, daemon=True).start()

                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            self._proc = HOOKPROC(hook_proc)
            self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
            ready.set()
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if self._hook:
                user32.UnhookWindowsHookEx(self._hook)
                self._hook = None

        def ptt_watchdog() -> None:
            """Prevent stuck Push-to-Talk if another window/UAC swallows WM_KEYUP."""
            while self._hook is not None:
                if self._ptt_active and self.ptt_vk:
                    if not (user32.GetAsyncKeyState(self.ptt_vk) & 0x8000):
                        self._ptt_active = False
                        threading.Thread(target=self.on_ptt_up, daemon=True).start()
                time.sleep(0.1)

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        ready.wait(timeout=2.0)
        threading.Thread(target=ptt_watchdog, daemon=True).start()

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
