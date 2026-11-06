"""Genera audio de prueba con el TTS de Windows (SAPI).

Sirve para validar la tuberia completa -- que cada motor carga, recibe el WAV
y devuelve texto -- SIN necesitar la voz del usuario. NO sustituye al corpus
real: una voz sintetica es limpia y monotona, asi que el WER que salga aqui
es optimista y no dice nada sobre como te transcribe a ti.

Uso:
    python sinteticas.py            # genera todas las frases
    python sinteticas.py --n 5      # solo las 5 primeras (mas rapido)
    python sinteticas.py --voces    # lista las voces TTS instaladas
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DESTINO = RAIZ / "grabaciones_sinteticas"
FRECUENCIA = 16_000


def powershell(script: str) -> str:
    proceso = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True,
    )
    if proceso.returncode != 0:
        raise RuntimeError(proceso.stderr.strip())
    return proceso.stdout.strip()


def listar_voces() -> list[str]:
    salida = powershell(
        "Add-Type -AssemblyName System.Speech; "
        "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
        ".GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
    )
    return [v.strip() for v in salida.splitlines() if v.strip()]


def elegir_voz() -> str | None:
    voces = listar_voces()
    for voz in voces:
        if any(p in voz.lower() for p in ("spanish", "espa", "helena", "pablo", "laura")):
            return voz
    return voces[0] if voces else None


def sintetizar(texto: str, destino: Path, voz: str | None) -> None:
    crudo = destino.with_suffix(".sapi.wav")
    seleccion = f"$s.SelectVoice('{voz}'); " if voz else ""
    limpio = texto.replace("'", "''")
    powershell(
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"{seleccion}"
        f"$s.SetOutputToWaveFile('{crudo}'); "
        f"$s.Speak('{limpio}'); $s.Dispose()"
    )
    # SAPI escribe a 22 kHz; los modelos ASR quieren 16 kHz mono.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(crudo),
         "-ar", str(FRECUENCIA), "-ac", "1", str(destino)],
        check=True,
    )
    crudo.unlink()


def leer_frases() -> list[str]:
    lineas = (RAIZ / "frases.txt").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.startswith("#")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None, help="solo las N primeras frases")
    ap.add_argument("--voces", action="store_true")
    args = ap.parse_args()

    if args.voces:
        for voz in listar_voces():
            print(voz)
        return

    voz = elegir_voz()
    if voz is None:
        sys.exit("No hay voces TTS instaladas en el sistema.")
    print(f"Voz: {voz}")
    if not any(p in voz.lower() for p in ("spanish", "espa", "helena", "pablo")):
        print("[!] No hay voz espanola instalada; el audio sonara con acento")
        print("    ingles y el WER sera artificialmente malo. Da igual para")
        print("    validar la tuberia, pero no lo interpretes como calidad.")

    DESTINO.mkdir(exist_ok=True)
    frases = leer_frases()[: args.n] if args.n else leer_frases()

    for i, frase in enumerate(frases, 1):
        destino = DESTINO / f"{i:02d}.wav"
        sintetizar(frase, destino, voz)
        print(f"  {destino.name}  {frase[:60]}...")

    print(f"\n{len(frases)} archivos en {DESTINO}")
    print("Ahora: python evaluar.py --grabaciones grabaciones_sinteticas")


if __name__ == "__main__":
    main()
