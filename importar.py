"""Convierte tus grabaciones largas en un corpus de prueba.

Hace tres cosas:
  1. extrae el audio (vale cualquier video o audio) y lo pasa a 16 kHz mono;
  2. lo trocea por los silencios en fragmentos cortos, del tamano de una frase
     dictada -- medir sobre una charla entera no predice como transcribe un
     dictado de 8 segundos;
  3. opcionalmente escribe un borrador de las transcripciones con large-v3
     para que solo tengas que corregirlo, en vez de teclearlo entero.

Uso:
    python importar.py "D:\\ruta\\charla.mp4"
    python importar.py "D:\\ruta\\charla.mp4" --nombre charla --max 25
    python importar.py "D:\\ruta\\charla.mp4" --borrador   # + transcribe

Deja grabaciones_<nombre>\\ con los WAV numerados y un referencias.txt.
IMPORTANTE: el borrador tiene errores a proposito de fabrica -- son los del
modelo. Hay que corregirlo a mano antes de medir nada, porque si no estarias
midiendo a los demas motores contra los aciertos y fallos de large-v3.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).parent
FRECUENCIA = 16_000
VENTANA = 0.03           # 30 ms por ventana de analisis
MIN_SEGMENTO = 2.5       # segundos; por debajo no parece una frase dictada
MAX_SEGMENTO = 15.0      # segundos; por encima, se parte
SILENCIO_CORTE = 0.45    # silencio minimo para considerar que hay una pausa
MARGEN = 0.15            # se deja algo de aire a cada lado del fragmento


def extraer_audio(origen: Path, destino: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(origen),
         "-ar", str(FRECUENCIA), "-ac", "1", "-vn", str(destino)],
        check=True,
    )


def detectar_voz(audio: np.ndarray) -> np.ndarray:
    """Devuelve una mascara booleana por ventana: True = hay voz.

    Umbral relativo al propio audio (percentil 20 del RMS), asi funciona
    igual con una grabacion bajita que con una alta.
    """
    n = int(VENTANA * FRECUENCIA)
    sobra = len(audio) % n
    recortado = audio[: len(audio) - sobra] if sobra else audio
    ventanas = recortado.reshape(-1, n)
    rms = np.sqrt((ventanas ** 2).mean(axis=1))

    suelo = np.percentile(rms, 20)
    techo = np.percentile(rms, 95)
    umbral = max(suelo * 3.0, techo * 0.06, 1e-4)
    return rms > umbral


def agrupar(mascara: np.ndarray) -> list[tuple[float, float]]:
    """Convierte la mascara de voz en tramos (inicio, fin) en segundos."""
    huecos = int(SILENCIO_CORTE / VENTANA)
    tramos: list[list[int]] = []
    inicio = None
    silencio = 0

    for i, hay_voz in enumerate(mascara):
        if hay_voz:
            if inicio is None:
                inicio = i
            silencio = 0
        elif inicio is not None:
            silencio += 1
            if silencio >= huecos:
                tramos.append([inicio, i - silencio + 1])
                inicio = None
    if inicio is not None:
        tramos.append([inicio, len(mascara)])

    segundos = [(a * VENTANA, b * VENTANA) for a, b in tramos]

    # Parte lo que se pase de largo y descarta lo que sea demasiado corto.
    resultado = []
    for a, b in segundos:
        duracion = b - a
        if duracion < MIN_SEGMENTO:
            continue
        if duracion <= MAX_SEGMENTO:
            resultado.append((a, b))
            continue
        trozos = int(np.ceil(duracion / MAX_SEGMENTO))
        paso = duracion / trozos
        resultado += [(a + i * paso, a + (i + 1) * paso) for i in range(trozos)]
    return resultado


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("origen", help="video o audio de partida")
    ap.add_argument("--nombre", default=None, help="nombre del corpus")
    ap.add_argument("--max", type=int, default=30, help="cuantos fragmentos como mucho")
    ap.add_argument("--borrador", action="store_true",
                    help="transcribe con large-v3 para que solo corrijas")
    args = ap.parse_args()

    origen = Path(args.origen)
    if not origen.exists():
        sys.exit(f"No existe: {origen}")

    nombre = args.nombre or origen.stem.lower().replace(" ", "_")[:24]
    destino = RAIZ / f"grabaciones_{nombre}"
    destino.mkdir(exist_ok=True)

    completo = destino / "_completo.wav"
    print(f"Extrayendo audio de {origen.name}...")
    extraer_audio(origen, completo)

    audio, _ = sf.read(completo, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    print(f"  {len(audio) / FRECUENCIA / 60:.1f} minutos de audio")

    tramos = agrupar(detectar_voz(audio))
    print(f"  {len(tramos)} fragmentos detectados entre silencios")
    if not tramos:
        sys.exit("No se detecto voz. Puede que el audio este muy bajo.")

    # Se queda con los mas largos: mas palabras por fragmento, medida mas estable.
    tramos = sorted(sorted(tramos, key=lambda t: t[1] - t[0], reverse=True)[: args.max])

    for i, (a, b) in enumerate(tramos, 1):
        ini = max(0, int((a - MARGEN) * FRECUENCIA))
        fin = min(len(audio), int((b + MARGEN) * FRECUENCIA))
        sf.write(destino / f"{i:02d}.wav", audio[ini:fin], FRECUENCIA, subtype="PCM_16")

    completo.unlink()
    print(f"  {len(tramos)} fragmentos guardados en {destino.name}")

    referencias = destino / "referencias.txt"
    if args.borrador:
        print("\nTranscribiendo el borrador con large-v3 (tarda un poco)...")
        import motores

        motor = motores.crear("whisper-large-v3-hf")
        lineas = ["# Borrador de large-v3: CORRIGELO antes de medir nada.",
                  "# Una linea por fragmento, en orden. Debe decir exactamente",
                  "# lo que se oye, o las metricas no valdran de nada.", ""]
        for wav in sorted(destino.glob("[0-9]*.wav")):
            texto = motor.transcribir(str(wav)).texto
            print(f"  {wav.name}  {texto[:70]}")
            lineas.append(texto)
        referencias.write_text("\n".join(lineas), encoding="utf-8")
        motor.liberar()
    elif not referencias.exists():
        lineas = ["# Una linea por fragmento, en orden, con lo que se oye.", ""]
        lineas += [f"# {w.name}" for w in sorted(destino.glob("[0-9]*.wav"))]
        referencias.write_text("\n".join(lineas), encoding="utf-8")

    print(f"\nAhora corrige {referencias} y luego:")
    print(f"  python evaluar.py --grabaciones {destino.name} --sufijo {nombre}")


if __name__ == "__main__":
    main()
