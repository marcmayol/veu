"""Compara motores ASR sobre tus grabaciones y saca una tabla con datos.

Uso:
    python evaluar.py                       # todos los motores disponibles
    python evaluar.py whisper-turbo-hf parakeet-tdt-0.6b-v3
    python evaluar.py --listar              # que motores hay y cuales faltan

Mide tres cosas, y las tres importan para dictado:
  WER       errores de palabra sobre la referencia (calidad)
  WER llano ignorando tildes y mayusculas (cuanto del error es solo ortografia)
  RTF       segundos de proceso por segundo de audio (latencia percibida)

Deja informe.md con las transcripciones completas: la tabla te dice cual gana,
el informe te dice EN QUE se equivoca, que es lo que decide de verdad.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import soundfile as sf

import motores

RAIZ = Path(__file__).parent
GRABACIONES = RAIZ / "grabaciones"
INFORME = RAIZ / "informe.md"

PUNTUACION = re.compile(r"[^\w\s]", re.UNICODE)
ESPACIOS = re.compile(r"\s+")

# Un motor que escribe "45" donde dijiste "cuarenta y cinco" NO se ha
# equivocado: para dictar es incluso lo que quieres. Sin esto, el WER penaliza
# el comportamiento correcto, y no lo hace por igual en todos los motores.
UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
DECENAS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
}
CENTENAS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
    "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600,
    "setecientos": 700, "ochocientos": 800, "novecientos": 900,
}
# Equivalencias que no son numeros pero sufren el mismo problema.
SINONIMOS = {"gigas": "gb", "giga": "gb", "gigabytes": "gb", "gigabyte": "gb"}


def _valor(palabra: str) -> int | None:
    return UNIDADES.get(palabra, DECENAS.get(palabra, CENTENAS.get(palabra)))


def numeros_a_digitos(palabras: list[str]) -> list[str]:
    """Convierte secuencias como 'cuarenta y cinco' en '45'.

    Cubre hasta 999 y el patron 'tres punto doce' -> '3.12', que es como se
    dictan las versiones. Suficiente para dictado; no pretende ser un parser
    completo del espanol.
    """
    salida: list[str] = []
    i = 0
    while i < len(palabras):
        valor = _valor(palabras[i])
        if valor is None:
            salida.append(SINONIMOS.get(palabras[i], palabras[i]))
            i += 1
            continue

        total = valor
        i += 1
        # centena + resto ("ciento veinte"), decena + y + unidad ("cuarenta y cinco")
        while i < len(palabras):
            if palabras[i] == "y" and i + 1 < len(palabras) and _valor(palabras[i + 1]):
                total += _valor(palabras[i + 1])  # type: ignore[operator]
                i += 2
            elif total >= 100 and _valor(palabras[i]) is not None:
                total += _valor(palabras[i])  # type: ignore[operator]
                i += 1
            else:
                break

        # decimales dictados: "tres punto doce"
        if i + 1 < len(palabras) and palabras[i] == "punto" and _valor(palabras[i + 1]):
            salida.append(f"{total}.{_valor(palabras[i + 1])}")
            i += 2
        else:
            salida.append(str(total))
    return salida


def normalizar(texto: str, quitar_tildes: bool = False,
               cifras: bool = False) -> list[str]:
    texto = texto.lower()
    # Protege el separador decimal ("3.12") antes de barrer la puntuacion.
    texto = re.sub(r"(?<=\d)[.,](?=\d)", "·", texto)
    texto = PUNTUACION.sub(" ", texto)
    texto = texto.replace("·", ".")
    if quitar_tildes or cifras:
        texto = "".join(
            c for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )
    palabras = ESPACIOS.sub(" ", texto).strip().split()
    return numeros_a_digitos(palabras) if cifras else palabras


def distancia(referencia: list[str], hipotesis: list[str]) -> int:
    """Levenshtein a nivel palabra."""
    previa = list(range(len(hipotesis) + 1))
    for i, palabra_ref in enumerate(referencia, 1):
        actual = [i]
        for j, palabra_hip in enumerate(hipotesis, 1):
            coste = 0 if palabra_ref == palabra_hip else 1
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + coste))
        previa = actual
    return previa[-1]


def leer_frases() -> list[str]:
    lineas = (RAIZ / "frases.txt").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.startswith("#")]


def cargar_muestras(carpeta: Path) -> list[tuple[Path, str]]:
    """Empareja cada WAV con su texto de referencia.

    Si la carpeta trae su propio referencias.txt (caso de un corpus importado
    de tus grabaciones), manda ese. Si no, se usa el frases.txt de siempre.
    """
    propio = carpeta / "referencias.txt"
    if propio.exists():
        lineas = propio.read_text(encoding="utf-8").splitlines()
        frases = [l.strip() for l in lineas if l.strip() and not l.startswith("#")]
    else:
        frases = leer_frases()

    muestras = []
    for wav in sorted(carpeta.glob("*.wav")):
        indice = int(wav.stem) - 1
        if 0 <= indice < len(frases):
            muestras.append((wav, frases[indice]))
    return muestras


def evaluar_motor(nombre: str, muestras: list[tuple[Path, str]]) -> dict | None:
    motor = motores.crear(nombre)
    ok, motivo = motor.disponible()
    if not ok:
        print(f"  saltado ({motivo})")
        return None

    fallos = fallos_llanos = fallos_utiles = palabras = 0
    tiempo_total = audio_total = 0.0
    detalle = []

    for wav, referencia in muestras:
        try:
            resultado = motor.transcribir(str(wav))
        except Exception as err:
            print(f"  [!] fallo en {wav.name}: {err}")
            return None

        ref = normalizar(referencia)
        hip = normalizar(resultado.texto)
        errores = distancia(ref, hip)
        errores_llanos = distancia(
            normalizar(referencia, True), normalizar(resultado.texto, True)
        )

        errores_utiles = distancia(
            normalizar(referencia, True, True), normalizar(resultado.texto, True, True)
        )

        fallos += errores
        fallos_llanos += errores_llanos
        fallos_utiles += errores_utiles
        palabras += len(ref)
        tiempo_total += resultado.segundos
        audio_total += sf.info(wav).duration

        detalle.append({
            "archivo": wav.name,
            "referencia": referencia,
            "transcripcion": resultado.texto,
            "errores": errores,
            "palabras": len(ref),
            "segundos": round(resultado.segundos, 2),
        })
        print(f"  {wav.name} {errores:>2}/{len(ref):<3} err  {resultado.segundos:>5.2f}s")

    motor.liberar()
    return {
        "motor": nombre,
        "wer": fallos / palabras,
        "wer_llano": fallos_llanos / palabras,
        "wer_util": fallos_utiles / palabras,
        "rtf": tiempo_total / audio_total,
        "segundos_por_frase": tiempo_total / len(muestras),
        "detalle": detalle,
    }


def recalcular(resultados: list[dict]) -> list[dict]:
    """Recomputa las metricas desde las transcripciones ya guardadas.

    Permite cambiar como se mide sin volver a pasar el audio por los modelos,
    que es lo caro. Las de tiempo (RTF, s/frase) se conservan tal cual.
    """
    for r in resultados:
        fallos = llanos = utiles = palabras = 0
        for d in r["detalle"]:
            ref, hip = d["referencia"], d["transcripcion"]
            errores = distancia(normalizar(ref), normalizar(hip))
            d["errores"] = errores
            d["palabras"] = len(normalizar(ref))
            fallos += errores
            llanos += distancia(normalizar(ref, True), normalizar(hip, True))
            utiles += distancia(normalizar(ref, True, True),
                                normalizar(hip, True, True))
            palabras += d["palabras"]
        r["wer"] = fallos / palabras
        r["wer_llano"] = llanos / palabras
        r["wer_util"] = utiles / palabras
    return resultados


def escribir_informe(resultados: list[dict]) -> Path:
    lineas = ["# Comparativa de motores ASR", "",
              "`WER util` es la metrica que manda: ignora tildes y cuenta como",
              "acierto que el motor escriba `45` donde dijiste *cuarenta y cinco*.",
              ""]
    lineas += ["| motor | WER util | WER | WER llano | RTF | s/frase |",
               "|---|---|---|---|---|---|"]
    for r in sorted(resultados, key=lambda x: x["wer_util"]):
        lineas.append(
            f"| {r['motor']} | **{r['wer_util']:.1%}** | {r['wer']:.1%} | "
            f"{r['wer_llano']:.1%} | {r['rtf']:.2f} | {r['segundos_por_frase']:.2f} |"
        )
    lineas.append("")

    for r in sorted(resultados, key=lambda x: x["wer_util"]):
        lineas += [f"## {r['motor']}", ""]
        peores = sorted(r["detalle"], key=lambda d: -d["errores"] / max(d["palabras"], 1))
        for d in peores:
            if d["errores"] == 0:
                continue
            lineas += [
                f"**{d['archivo']}** ({d['errores']}/{d['palabras']} errores)",
                "",
                f"- esperado: {d['referencia']}",
                f"- obtenido: {d['transcripcion']}",
                "",
            ]
        if all(d["errores"] == 0 for d in r["detalle"]):
            lineas += ["Sin errores.", ""]

    INFORME.write_text("\n".join(lineas), encoding="utf-8")
    return INFORME


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("nombres", nargs="*", help="motores a evaluar (por defecto: todos)")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--grabaciones", default="grabaciones",
                    help="carpeta con los WAV (por defecto: grabaciones)")
    ap.add_argument("--sufijo", default="",
                    help="sufijo para informe.md y resultados.json")
    ap.add_argument("--recalcular", action="store_true",
                    help="rehace las metricas desde el JSON, sin tocar los modelos")
    args = ap.parse_args()

    if args.listar:
        for nombre, ok, motivo, desc in motores.inventario():
            estado = "OK" if ok else f"-- {motivo}"
            print(f"{nombre:<24} {estado:<28} {desc}")
        return

    global INFORME
    carpeta = Path(args.grabaciones)
    if not carpeta.is_absolute():
        carpeta = RAIZ / carpeta
    if args.sufijo:
        INFORME = RAIZ / f"informe_{args.sufijo}.md"

    nombre_json = f"resultados_{args.sufijo}.json" if args.sufijo else "resultados.json"

    if args.recalcular:
        origen = RAIZ / nombre_json
        if not origen.exists():
            sys.exit(f"No existe {origen.name}; hay que evaluar al menos una vez.")
        resultados = recalcular(json.loads(origen.read_text(encoding="utf-8")))
    else:
        muestras = cargar_muestras(carpeta)
        if not muestras:
            sys.exit(f"No hay WAV en {carpeta}. Ejecuta primero: python grabar.py")
        print(f"{len(muestras)} muestras de {carpeta.name}.\n")

        nombres = args.nombres or [n for n, ok, _, _ in motores.inventario() if ok]
        resultados = []
        for nombre in nombres:
            print(f"== {nombre}")
            resultado = evaluar_motor(nombre, muestras)
            if resultado:
                resultados.append(resultado)
                print(f"  -> WER {resultado['wer']:.1%}  RTF {resultado['rtf']:.2f}\n")

        if not resultados:
            sys.exit("Ningun motor pudo evaluarse.")

    (RAIZ / nombre_json).write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    informe = escribir_informe(resultados)

    print(f"{'motor':<24} {'WER util':>9} {'WER':>7} {'llano':>7} "
          f"{'RTF':>6} {'s/frase':>8}")
    print("-" * 66)
    for r in sorted(resultados, key=lambda x: x["wer_util"]):
        print(f"{r['motor']:<24} {r['wer_util']:>8.1%} {r['wer']:>6.1%} "
              f"{r['wer_llano']:>6.1%} {r['rtf']:>6.2f} "
              f"{r['segundos_por_frase']:>8.2f}")
    print(f"\nDetalle de errores en {informe.name}")


if __name__ == "__main__":
    main()
