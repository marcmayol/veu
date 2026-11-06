"""Graba el corpus de referencia con tu voz.

Uso:
    python grabar.py            # graba solo las frases que falten
    python grabar.py --rehacer  # vuelve a grabarlas todas
    python grabar.py --frase 7  # repite solo la frase numero 7

Enter para empezar a grabar, Enter otra vez para parar. Si te trabas, escribe
r y Enter al terminar para repetir la toma.
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

RAIZ = Path(__file__).parent
GRABACIONES = RAIZ / "grabaciones"
FRECUENCIA = 16_000


def leer_frases() -> list[str]:
    lineas = (RAIZ / "frases.txt").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.startswith("#")]


def grabar_hasta_enter() -> np.ndarray:
    trozos: queue.Queue[np.ndarray] = queue.Queue()
    parar = threading.Event()

    def callback(datos, frames, tiempo, estado):
        if estado:
            print(estado, file=sys.stderr)
        trozos.put(datos.copy())

    def esperar_tecla():
        parar.orden = input()  # type: ignore[attr-defined]
        parar.set()

    hilo = threading.Thread(target=esperar_tecla, daemon=True)
    hilo.start()

    with sd.InputStream(samplerate=FRECUENCIA, channels=1, dtype="float32",
                        callback=callback):
        while not parar.is_set():
            sd.sleep(50)

    audio = []
    while not trozos.empty():
        audio.append(trozos.get())
    orden = getattr(parar, "orden", "")
    return (np.concatenate(audio) if audio else np.zeros((0, 1), "float32")), orden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rehacer", action="store_true")
    ap.add_argument("--frase", type=int, default=None, help="numero de frase (1..N)")
    args = ap.parse_args()

    GRABACIONES.mkdir(exist_ok=True)
    frases = leer_frases()

    print(f"Dispositivo de entrada: {sd.query_devices(kind='input')['name']}")
    print(f"{len(frases)} frases en el corpus.\n")

    indices = range(len(frases)) if args.frase is None else [args.frase - 1]

    for i in indices:
        destino = GRABACIONES / f"{i + 1:02d}.wav"
        if destino.exists() and not args.rehacer and args.frase is None:
            continue

        while True:
            print(f"\n[{i + 1}/{len(frases)}] {frases[i]}")
            input("    Enter para GRABAR...")
            print("    ● grabando... (Enter para parar, 'r'+Enter para repetir)")
            audio, orden = grabar_hasta_enter()

            if len(audio) == 0:
                print("    [!] no se capturo audio, repito")
                continue

            duracion = len(audio) / FRECUENCIA
            pico = float(np.abs(audio).max())
            print(f"    {duracion:.1f} s, pico {pico:.2f}")

            if orden.strip().lower() == "r":
                continue
            if duracion < 0.4:
                print("    [!] demasiado corto, repito")
                continue
            if pico < 0.01:
                print("    [!] practicamente silencio, repito")
                continue

            sf.write(destino, audio, FRECUENCIA, subtype="PCM_16")
            print(f"    guardado en {destino.name}")
            break

    hechas = len(list(GRABACIONES.glob("*.wav")))
    print(f"\nListo: {hechas}/{len(frases)} frases grabadas en {GRABACIONES}")


if __name__ == "__main__":
    main()
