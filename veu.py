"""Veu: dictado por voz en cualquier ventana, 100 % local y en CPU.

Mantén pulsado el atajo (por defecto, la barra espaciadora), habla y suelta:
el texto aparece donde esté el cursor. Una pulsación corta del espacio sigue
escribiendo un espacio normal. Esc mientras escucha cancela.

Motor: Parakeet-TDT 0.6b v3 (int8, ONNX) con sherpa-onnx. No usa red.
Configuración: veu.json junto al ejecutable (se crea la primera vez).
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk

import numpy as np

# --------------------------------------------------------------------------- rutas

if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

CONFIG = os.path.join(BASE, "veu.json")
LOG = os.path.join(BASE, "veu.log")
MODELOS_POSIBLES = [
    os.path.join(BASE, "modelo"),
    r"D:\Veu\asr\sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
]

logging.basicConfig(filename=LOG, level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("veu")

TERMINALES = ["WindowsTerminal.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
              "conhost.exe", "wezterm-gui.exe", "alacritty.exe"]

CONFIG_DEFECTO = {
    "atajo": "espacio",
    "_atajo": "Una tecla sola ('espacio', 'f8', 'bloq mayus'...) se mantiene pulsada para dictar "
              "y si la tocas rápido hace lo de siempre. O una combinación: 'alt+espacio', "
              "'ctrl+win', 'ctrl+shift+d'...",
    "mantener_ms": 350,
    "_mantener_ms": "Cuánto hay que mantener una tecla sola para que empiece a escuchar.",
    "punto_final": True,
    "_punto_final": "false quita el punto del final (cómodo para buscadores).",
    "reemplazos": {
        "Campous": "Compose",
        "que histore": "keystore",
        "que historie": "keystore",
        "camit": "commit",
        "Lora": "LoRA",
    },
    "_reemplazos": "Palabra o frase que entiende mal -> la buena. No distingue mayúsculas.",
    "excluir_apps": TERMINALES,
    "_excluir_apps": "Programas donde Veu no hace nada. Por defecto los terminales, donde Claude Code "
                     "y otros agentes ya tienen su propio dictado. [] para dictar en todas partes.",
    "activar_desactivar": "ctrl+alt+espacio",
    "_activar_desactivar": "Combinación que enciende y apaga Veu. \"\" para no usar ninguna.",
    "hilos": 4,
    "microfono": None,
    "_microfono": "null = el predeterminado de Windows; o parte de su nombre.",
}


def cargar_config() -> dict:
    cfg = dict(CONFIG_DEFECTO)
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:  # noqa: BLE001
            log.error("veu.json no se puede leer: %s", e)
    else:
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG_DEFECTO, f, ensure_ascii=False, indent=2)
    return cfg


# --------------------------------------------------------------------------- Win32

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
LLKHF_INJECTED = 0x10
KEYEVENTF_KEYUP = 0x2
INPUT_KEYBOARD = 1
MARCA = 0x56455521  # dwExtraInfo de nuestras pulsaciones simuladas
DEPURAR = bool(os.environ.get("VEU_DEBUG"))

ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _U)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
kernel32.GetModuleHandleW.restype = wt.HMODULE
user32.OpenClipboard.argtypes = [wt.HWND]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wt.UINT]
user32.SetClipboardData.argtypes = [wt.UINT, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.RegisterClipboardFormatW.argtypes = [wt.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wt.UINT
kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, wt.LONG]
user32.GetParent.argtypes = [wt.HWND]
user32.GetParent.restype = wt.HWND

VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_ESCAPE = 0x10, 0x11, 0x12, 0x5B, 0x5C, 0x1B
VK_RELLENO = 0xE8  # sin asignar: evita que Alt/Win soltados solos abran menú o Inicio

MODIFICADORES = {
    "ctrl": (VK_CONTROL, {0xA2, 0xA3, VK_CONTROL}),
    "control": (VK_CONTROL, {0xA2, 0xA3, VK_CONTROL}),
    "alt": (VK_MENU, {0xA4, 0xA5, VK_MENU}),
    "shift": (VK_SHIFT, {0xA0, 0xA1, VK_SHIFT}),
    "mayus": (VK_SHIFT, {0xA0, 0xA1, VK_SHIFT}),
    "win": (VK_LWIN, {VK_LWIN, VK_RWIN}),
}
TECLAS = {
    "espacio": 0x20, "space": 0x20, "enter": 0x0D, "intro": 0x0D, "tab": 0x09,
    "bloq mayus": 0x14, "capslock": 0x14, "insert": 0x2D, "pausa": 0x13, "pause": 0x13,
    "inicio": 0x24, "home": 0x24, "fin": 0x23, "end": 0x23, "menu": 0x5D,
    "bloq despl": 0x91, "scrolllock": 0x91,
}
TECLAS.update({f"f{i}": 0x6F + i for i in range(1, 25)})
TECLAS.update({chr(c).lower(): c for c in range(0x41, 0x5B)})
TECLAS.update({str(d): 0x30 + d for d in range(10)})


kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
user32.GetForegroundWindow.restype = wt.HWND


def app_delante() -> str:
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(520)
        n = wt.DWORD(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return os.path.basename(buf.value).lower()
        return ""
    finally:
        kernel32.CloseHandle(h)


def pulsada(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def enviar(*teclas: tuple[int, bool]) -> None:
    """Envía (vk, soltar) en orden, marcadas para que el hook las ignore."""
    arr = (INPUT * len(teclas))()
    for i, (vk, arriba) in enumerate(teclas):
        arr[i].type = INPUT_KEYBOARD
        arr[i].u.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP if arriba else 0, 0, MARCA)
    user32.SendInput(len(teclas), arr, ctypes.sizeof(INPUT))


# --------------------------------------------------------------------------- portapapeles

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x2
FMT_SIN_HISTORIAL = user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")


def _abrir_portapapeles() -> bool:
    for _ in range(20):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def leer_portapapeles() -> str | None:
    if not _abrir_portapapeles():
        return None
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def poner_portapapeles(texto: str, sin_historial: bool) -> None:
    if not _abrir_portapapeles():
        raise RuntimeError("portapapeles ocupado")
    try:
        user32.EmptyClipboard()
        datos = ctypes.create_unicode_buffer(texto)
        n = ctypes.sizeof(datos)
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, n)
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, datos, n)
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        if sin_historial:  # que el dictado no quede en Win+V ni se sincronice
            h2 = kernel32.GlobalAlloc(GMEM_MOVEABLE, 4)
            user32.SetClipboardData(FMT_SIN_HISTORIAL, h2)
    finally:
        user32.CloseClipboard()


def pegar(texto: str) -> None:
    # Espera a que sueltes los modificadores, o Ctrl+V llegaría como Ctrl+Alt+V
    fin = time.time() + 1.5
    while time.time() < fin and any(pulsada(v) for v in (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN)):
        time.sleep(0.02)
    anterior = leer_portapapeles()
    poner_portapapeles(texto, sin_historial=True)
    enviar((VK_CONTROL, False), (0x56, False), (0x56, True), (VK_CONTROL, True))
    time.sleep(0.35)  # Teams y otras apps Electron leen el portapapeles con retraso
    if anterior is not None:
        poner_portapapeles(anterior, sin_historial=True)


# --------------------------------------------------------------------------- motor

class Motor:
    def __init__(self, hilos: int):
        self.rec = None
        self.listo = threading.Event()
        self.error: str | None = None
        self.hilos = hilos

    def cargar(self) -> None:
        try:
            import sherpa_onnx
            d = next((m for m in MODELOS_POSIBLES if os.path.exists(os.path.join(m, "tokens.txt"))), None)
            if not d:
                raise FileNotFoundError("no encuentro la carpeta 'modelo' junto a Veu")
            t = time.time()
            self.rec = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=os.path.join(d, "encoder.int8.onnx"),
                decoder=os.path.join(d, "decoder.int8.onnx"),
                joiner=os.path.join(d, "joiner.int8.onnx"),
                tokens=os.path.join(d, "tokens.txt"),
                model_type="nemo_transducer", num_threads=self.hilos)
            log.info("modelo cargado de %s en %.1f s", d, time.time() - t)
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
            log.exception("no se pudo cargar el modelo")
        self.listo.set()

    def transcribir(self, audio: np.ndarray) -> str:
        s = self.rec.create_stream()
        s.accept_waveform(16000, audio)
        self.rec.decode_stream(s)
        return s.result.text.strip()


def pulir(texto: str, cfg: dict) -> str:
    for mal, bien in (cfg.get("reemplazos") or {}).items():
        texto = re.sub(rf"(?<!\w){re.escape(mal)}(?!\w)", bien, texto, flags=re.IGNORECASE)
    if not cfg.get("punto_final", True):
        texto = re.sub(r"\.$", "", texto)
    return texto


# --------------------------------------------------------------------------- grabación

class Grabadora:
    def __init__(self, microfono):
        self.microfono = microfono
        self.trozos: list[np.ndarray] = []
        self.stream = None
        self.nivel = 0.0

    def _dispositivo(self):
        if not self.microfono:
            return None
        import sounddevice as sd
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and self.microfono.lower() in d["name"].lower():
                return i
        return None

    def empezar(self) -> None:
        import sounddevice as sd
        self.trozos = []

        def cb(data, frames, t, status):
            self.trozos.append(data[:, 0].copy())
            self.nivel = float(np.sqrt(np.mean(data[:, 0] ** 2)))

        self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                     device=self._dispositivo(), callback=cb)
        self.stream.start()

    def parar(self) -> np.ndarray:
        prueba = os.environ.get("VEU_PRUEBA_WAV")  # solo para pruebas automáticas
        if prueba:
            import wave
            with wave.open(prueba) as w:
                a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            if self.stream:
                self.stream.stop(); self.stream.close(); self.stream = None
            return a
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.nivel = 0.0
        return np.concatenate(self.trozos) if self.trozos else np.zeros(0, np.float32)


# --------------------------------------------------------------------------- atajo

def parsear_atajo(texto: str):
    partes = [p.strip().lower() for p in texto.replace(" + ", "+").split("+") if p.strip()]
    mods = [MODIFICADORES[p] for p in partes[:-1] if p in MODIFICADORES]
    ultima = partes[-1]
    if ultima in MODIFICADORES:
        vk_principal, conjunto = MODIFICADORES[ultima]
    elif ultima in TECLAS:
        vk_principal, conjunto = TECLAS[ultima], {TECLAS[ultima]}
    else:
        raise ValueError(f"no conozco la tecla '{ultima}'")
    return mods, vk_principal, conjunto


class Atajo:
    """Hook de teclado global. Dos modos:
    - tecla sola: mantener = dictar; pulsación corta o si tecleas otra tecla = la tecla de siempre.
    - combinación: con los modificadores pulsados, la tecla principal dicta mientras la mantienes.
    """

    def __init__(self, cfg: dict, al_empezar, al_terminar, al_cancelar):
        self.mods, self.vk, self.conjunto = parsear_atajo(cfg["atajo"])
        self.sola = not self.mods
        self.mantener = cfg.get("mantener_ms", 350) / 1000
        self.al_empezar, self.al_terminar, self.al_cancelar = al_empezar, al_terminar, al_cancelar
        self.excluir = {a.lower() for a in cfg.get("excluir_apps") or []}
        conmutar = (cfg.get("activar_desactivar") or "").strip()
        self.conmutar = parsear_atajo(conmutar) if conmutar else None
        self.al_conmutar = None
        self.activo = True
        self._tragar_arriba: set[int] = set()
        self.estado = "libre"  # libre | pendiente | grabando
        self.pulsacion = 0
        self.lock = threading.Lock()
        self._proc = HOOKPROC(self._hook)

    def _mods_ok(self) -> bool:
        return all(pulsada(vk) for vk, _ in self.mods)

    def _otros_mods(self) -> bool:
        return any(pulsada(v) for v in (VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_SHIFT))

    def _timer(self, n: int) -> None:
        with self.lock:
            if self.estado != "pendiente" or self.pulsacion != n:
                return
            self.estado = "grabando"
        self.al_empezar()

    def _hook(self, ncode, wparam, lparam):
        if ncode == 0:
            k = KBDLLHOOKSTRUCT.from_address(lparam)
            if k.dwExtraInfo != MARCA:
                abajo = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                antes = self.estado
                tragar = self._tecla(k.vkCode, abajo)
                if DEPURAR:
                    log.info("tecla %#x %s %s->%s %s", k.vkCode, "abajo" if abajo else "arriba",
                             antes, self.estado, "TRAGADA" if tragar else "")
                if tragar:
                    return 1
        return user32.CallNextHookEx(None, ncode, wparam, lparam)

    def _tecla(self, vk: int, abajo: bool) -> bool:
        """Devuelve True si hay que tragarse la tecla."""
        with self.lock:
            # --- atajo de activar/desactivar
            if vk in self._tragar_arriba and not abajo:
                self._tragar_arriba.discard(vk)
                return True
            if self.conmutar and abajo and vk in self.conmutar[2] and self.conmutar[0]                     and all(pulsada(m) for m, _ in self.conmutar[0]):
                self._tragar_arriba.add(vk)
                enviar((VK_RELLENO, False), (VK_RELLENO, True))
                if self.al_conmutar:
                    threading.Thread(target=self.al_conmutar, daemon=True).start()
                return True
            if not self.activo:
                return False
            estado = self.estado
            # --- Esc cancela mientras escucha
            if estado == "grabando" and vk == VK_ESCAPE and abajo:
                self.estado = "libre"
                threading.Thread(target=self.al_cancelar, daemon=True).start()
                return True

            es_principal = vk in self.conjunto
            if self.sola:
                if es_principal:
                    if abajo:
                        if estado == "libre":
                            if self._otros_mods() or (self.excluir and app_delante() in self.excluir):
                                return False  # Ctrl+Espacio y compañía siguen funcionando
                            self.estado = "pendiente"
                            self.pulsacion += 1
                            threading.Timer(self.mantener, self._timer, (self.pulsacion,)).start()
                        return True  # repeticiones también se tragan
                    # soltar
                    if estado == "pendiente":
                        self.estado = "libre"
                        enviar((self.vk, False), (self.vk, True))  # toque corto = tecla normal
                        return True
                    if estado == "grabando":
                        self.estado = "libre"
                        threading.Thread(target=self.al_terminar, daemon=True).start()
                        return True
                    return False
                # otra tecla mientras la principal está a medias: estabas escribiendo
                if estado == "pendiente" and abajo:
                    self.estado = "libre"
                    enviar((self.vk, False), (self.vk, True), (vk, False))
                    return True
                return False

            # --- modo combinación
            if es_principal and abajo:
                if estado == "grabando":
                    return True
                if self._mods_ok() and not (self.excluir and app_delante() in self.excluir):
                    self.estado = "grabando"
                    enviar((VK_RELLENO, False), (VK_RELLENO, True))
                    threading.Thread(target=self.al_empezar, daemon=True).start()
                    return True
                return False
            if estado == "grabando" and not abajo:
                soltada_mod = any(vk in conj for _, conj in self.mods)
                if es_principal or soltada_mod:
                    self.estado = "libre"
                    enviar((VK_RELLENO, False), (VK_RELLENO, True))
                    threading.Thread(target=self.al_terminar, daemon=True).start()
                    return es_principal
            return False

    def bucle(self) -> None:
        h = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        if not h:
            log.error("SetWindowsHookEx falló: %s", ctypes.get_last_error())
            return
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


# --------------------------------------------------------------------------- aviso en pantalla

class Aviso:
    """Pastilla flotante abajo en el centro. Nunca roba el foco: se mueve fuera
    de la pantalla en vez de ocultarse, y lleva WS_EX_NOACTIVATE."""

    FUERA = "+-3000+-3000"

    def __init__(self, root: tk.Tk):
        self.root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.configure(bg="#1b1b1f")
        self.lienzo = tk.Canvas(root, width=14, height=14, bg="#1b1b1f", highlightthickness=0)
        self.lienzo.pack(side="left", padx=(14, 6), pady=10)
        self.punto = self.lienzo.create_oval(2, 2, 12, 12, fill="#d62828", outline="")
        self.etiqueta = tk.Label(root, text="", fg="#f2f2f2", bg="#1b1b1f", font=("Segoe UI", 11))
        self.etiqueta.pack(side="left", padx=(0, 16), pady=8)
        root.geometry(self.FUERA)
        root.update_idletasks()
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST = -20, 0x08000000, 0x80, 0x8
        estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, estilo | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)

    def mostrar(self, texto: str, color: str = "#d62828") -> None:
        def _():
            self.etiqueta.config(text=texto)
            self.lienzo.itemconfig(self.punto, fill=color)
            self.root.update_idletasks()
            w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
            x = (self.root.winfo_screenwidth() - w) // 2
            y = self.root.winfo_screenheight() - h - 90
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.after(0, _)

    def ocultar(self, tras_ms: int = 0) -> None:
        self.root.after(tras_ms, lambda: self.root.geometry(self.FUERA))


# --------------------------------------------------------------------------- app

class Veu:
    def __init__(self):
        self.cfg = cargar_config()
        self.motor = Motor(int(self.cfg.get("hilos", 4)))
        self.grab = Grabadora(self.cfg.get("microfono"))
        self.trabajo: queue.Queue = queue.Queue()
        self.root = tk.Tk()
        self.aviso = Aviso(self.root)
        self.atajo = Atajo(self.cfg, self._empezar, self._terminar, self._cancelar)
        self.atajo.al_conmutar = self.conmutar
        self.icono = None

    def conmutar(self, *_) -> None:
        self.atajo.activo = not self.atajo.activo
        if self.atajo.activo:
            self.aviso.mostrar("Veu activado", "#2e9e4f")
        else:
            self.aviso.mostrar("Veu desactivado", "#888888")
        self.aviso.ocultar(1200)
        if self.icono:
            self.icono.update_menu()

    def _terminal_activo(self, *_) -> bool:
        return not any(t.lower() in self.atajo.excluir for t in TERMINALES)

    def _alternar_terminal(self, *_) -> None:
        excl = [a for a in (self.cfg.get("excluir_apps") or [])]
        if self._terminal_activo():
            excl += [t for t in TERMINALES if t not in excl]
        else:
            excl = [a for a in excl if a.lower() not in {t.lower() for t in TERMINALES}]
        self.cfg["excluir_apps"] = excl
        self.atajo.excluir = {a.lower() for a in excl}
        self._guardar_config()
        if self.icono:
            self.icono.update_menu()

    def _guardar_config(self) -> None:
        try:
            with open(CONFIG, encoding="utf-8") as f:
                disco = json.load(f)
        except Exception:  # noqa: BLE001
            disco = dict(CONFIG_DEFECTO)
        disco["excluir_apps"] = self.cfg["excluir_apps"]
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(disco, f, ensure_ascii=False, indent=2)
        self.grabando_desde = 0.0

    # llamadas desde el hilo del atajo
    def _empezar(self) -> None:
        if not self.motor.listo.is_set():
            self.aviso.mostrar("Veu aún está cargando…", "#888888")
            self.aviso.ocultar(1500)
        try:
            self.grab.empezar()
            self.grabando_desde = time.time()
            self.aviso.mostrar("Escuchando…   Esc cancela")
            self.root.after(0, self._latido)
        except Exception as e:  # noqa: BLE001
            log.exception("micrófono")
            self.aviso.mostrar(f"Sin micrófono: {e}", "#888888")
            self.aviso.ocultar(2500)

    def _latido(self) -> None:
        if self.grab.stream is None:
            return
        n = min(1.0, self.grab.nivel * 12)
        r = 3 - 2 * n
        self.aviso.lienzo.coords(self.aviso.punto, r, r, 14 - r, 14 - r)
        self.root.after(60, self._latido)

    def _terminar(self) -> None:
        audio = self.grab.parar()
        self.trabajo.put(audio)

    def _cancelar(self) -> None:
        self.grab.parar()
        self.aviso.mostrar("Cancelado", "#888888")
        self.aviso.ocultar(700)

    def _procesar(self) -> None:
        while True:
            audio = self.trabajo.get()
            if len(audio) < 16000 * 0.3:
                self.aviso.ocultar()
                continue
            self.aviso.mostrar("Escribiendo…", "#e0a100")
            self.motor.listo.wait()
            if self.motor.error:
                self.aviso.mostrar(f"Error del modelo: {self.motor.error}", "#888888")
                self.aviso.ocultar(4000)
                continue
            try:
                t = time.time()
                texto = pulir(self.motor.transcribir(audio), self.cfg)
                log.info("%.1f s de audio en %.2f s: %r", len(audio) / 16000, time.time() - t, texto)
                if texto:
                    pegar(texto)
                self.aviso.ocultar()
            except Exception as e:  # noqa: BLE001
                log.exception("transcribir/pegar")
                self.aviso.mostrar(f"Error: {e}", "#888888")
                self.aviso.ocultar(3000)

    def _bandeja(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 60, 60), fill=(214, 40, 40, 255))
        d.rounded_rectangle((24, 14, 40, 40), radius=8, fill="white")
        d.arc((17, 24, 47, 48), 0, 180, fill="white", width=4)
        d.line((32, 48, 32, 54), fill="white", width=4)

        def abrir_config(*_):
            os.startfile(CONFIG)

        def salir(icon, *_):
            icon.stop()
            self.root.after(0, self.root.destroy)

        tecla = self.cfg.get("activar_desactivar") or ""
        menu = pystray.Menu(
            pystray.MenuItem(f"Dictar: mantén «{self.cfg['atajo']}»", None, enabled=False),
            pystray.MenuItem(f"Activado ({tecla})" if tecla else "Activado", self.conmutar,
                             checked=lambda _: self.atajo.activo),
            pystray.MenuItem("Dictar también en terminales", self._alternar_terminal,
                             checked=lambda _: self._terminal_activo()),
            pystray.MenuItem("Configuración (reinicia Veu tras guardar)", abrir_config),
            pystray.MenuItem("Salir", salir),
        )
        self.icono = pystray.Icon("Veu", img, "Veu · dictado local", menu)
        self.icono.run_detached()

    def correr(self) -> None:
        threading.Thread(target=self.motor.cargar, daemon=True).start()
        threading.Thread(target=self._procesar, daemon=True).start()
        threading.Thread(target=self.atajo.bucle, daemon=True).start()
        self._bandeja()
        log.info("Veu arrancado, atajo=%s", self.cfg["atajo"])
        self.root.mainloop()
        os._exit(0)


def main() -> None:
    # una sola instancia
    kernel32.CreateMutexW(None, False, "Local\\VeuDictado")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        pass
    Veu().correr()


if __name__ == "__main__":
    main()
