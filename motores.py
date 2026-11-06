"""Adaptadores de motores ASR intercambiables.

Cada motor implementa la misma interfaz: se comprueba si esta disponible,
se carga una vez, y transcribe un WAV de 16 kHz mono a texto.

El resto de la app (banco de pruebas y, mas adelante, el dictado global)
solo habla con esta interfaz. Cambiar de modelo = cambiar una cadena.
"""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass, field


def _hay(paquete: str) -> bool:
    return importlib.util.find_spec(paquete) is not None


@dataclass
class Resultado:
    texto: str
    segundos: float


class Motor:
    """Interfaz comun. Los adaptadores heredan y rellenan los huecos."""

    nombre = "base"
    descripcion = ""
    paquetes: tuple[str, ...] = ()

    def __init__(self, dispositivo: str = "cuda"):
        self.dispositivo = dispositivo
        self._modelo = None

    def disponible(self) -> tuple[bool, str]:
        faltan = [p for p in self.paquetes if not _hay(p)]
        if faltan:
            return False, "falta " + ", ".join(faltan)
        return True, ""

    def cargar(self) -> None:
        raise NotImplementedError

    def _transcribir(self, wav: str) -> str:
        raise NotImplementedError

    def transcribir(self, wav: str) -> Resultado:
        if self._modelo is None:
            self.cargar()
        inicio = time.perf_counter()
        texto = self._transcribir(wav)
        return Resultado(texto.strip(), time.perf_counter() - inicio)

    def liberar(self) -> None:
        self._modelo = None
        if _hay("torch"):
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()


# ---------------------------------------------------------------------------
# Whisper via transformers (torch cu128) - la via segura en Blackwell
# ---------------------------------------------------------------------------
class WhisperTransformers(Motor):
    nombre = "whisper-turbo-hf"
    descripcion = "openai/whisper-large-v3-turbo sobre transformers + torch"
    paquetes = ("torch", "transformers")

    modelo_id = "openai/whisper-large-v3-turbo"

    def cargar(self) -> None:
        import torch
        from transformers import pipeline

        self._modelo = pipeline(
            "automatic-speech-recognition",
            model=self.modelo_id,
            torch_dtype=torch.float16 if self.dispositivo == "cuda" else torch.float32,
            device=0 if self.dispositivo == "cuda" else -1,
        )

    def _transcribir(self, wav: str) -> str:
        salida = self._modelo(
            wav,
            generate_kwargs={"language": "es", "task": "transcribe"},
            return_timestamps=False,
        )
        return salida["text"]


class WhisperLargeV3(WhisperTransformers):
    nombre = "whisper-large-v3-hf"
    descripcion = "openai/whisper-large-v3 completo (mas lento, mas preciso)"
    modelo_id = "openai/whisper-large-v3"


# ---------------------------------------------------------------------------
# faster-whisper (CTranslate2). Puede no traer kernels para sm_120 (Blackwell);
# si peta en CUDA, cae a CPU con int8 en vez de morir.
# ---------------------------------------------------------------------------
class FasterWhisper(Motor):
    nombre = "faster-whisper-turbo"
    descripcion = "CTranslate2, el mas rapido de los Whisper si soporta tu GPU"
    paquetes = ("faster_whisper",)

    modelo_id = "large-v3-turbo"

    def cargar(self) -> None:
        from faster_whisper import WhisperModel

        try:
            self._modelo = WhisperModel(
                self.modelo_id, device="cuda", compute_type="float16"
            )
        except Exception as err:  # sm_120 sin kernels, driver, etc.
            print(f"  [!] CUDA no disponible para faster-whisper ({err}); uso CPU int8")
            self._modelo = WhisperModel(
                self.modelo_id, device="cpu", compute_type="int8"
            )

    # Vocabulario con el que se sesga el decodificador. Es la palanca mas
    # barata que existe para los nombres propios tecnicos: sin esto, "keystore"
    # sale como "que historie" y "Compose" como "CampoUS".
    JERGA = (
        "Gradle, Compose, versionCode, Kotlin, LoRA, VRAM, DataStore, keystore, "
        "APK, webhook, n8n, CORS, SVG, pip, litertlm, Gemma, BBVA, Balua, Arta, "
        "RTX, batch, pipeline, commit, release, script, anchor mode."
    )
    prompt: str | None = None

    def _transcribir(self, wav: str) -> str:
        segmentos, _ = self._modelo.transcribe(
            wav, language="es", beam_size=5, initial_prompt=self.prompt
        )
        return "".join(s.text for s in segmentos)


class FasterWhisperJerga(FasterWhisper):
    nombre = "faster-whisper-jerga"
    descripcion = "igual que el anterior pero sesgado con tu vocabulario tecnico"

    def __init__(self, dispositivo: str = "cuda"):
        super().__init__(dispositivo)
        self.prompt = self.JERGA


# ---------------------------------------------------------------------------
# NVIDIA Parakeet TDT 0.6B v3 - multilingue (25 idiomas europeos, es incluido).
# Modelo pequeno y muy rapido; el candidato serio a destronar a Whisper.
#
# transformers lo soporta de forma nativa (ParakeetForCTC / ForRNNT / ForTDT),
# asi que NO hace falta NeMo, que en Windows da bastante guerra.
# ---------------------------------------------------------------------------
class ParakeetTDT(Motor):
    nombre = "parakeet-tdt-0.6b-v3"
    descripcion = "NVIDIA, 600M parametros, disenado para baja latencia"
    paquetes = ("torch", "transformers")

    modelo_id = "nvidia/parakeet-tdt-0.6b-v3"

    def cargar(self) -> None:
        from transformers import pipeline

        self._modelo = pipeline(
            "automatic-speech-recognition",
            model=self.modelo_id,
            device=0 if self.dispositivo == "cuda" else -1,
        )

    def _transcribir(self, wav: str) -> str:
        return self._modelo(wav)["text"]


class Canary(Motor):
    """Canary solo se puede usar via NeMo, que no es viable en Windows nativo.

    Queda registrado a proposito para que aparezca como no disponible y no se
    nos olvide: si el resto de motores decepcionan, la salida es correrlo en
    WSL, igual que se hizo con litert-torch.
    """

    nombre = "canary-1b-v2"
    descripcion = "NVIDIA Canary 1B v2 (requiere NeMo; solo viable en WSL)"
    paquetes = ("nemo",)

    modelo_id = "nvidia/canary-1b-v2"

    def cargar(self) -> None:
        import nemo.collections.asr as nemo_asr

        self._modelo = nemo_asr.models.ASRModel.from_pretrained(self.modelo_id)
        if self.dispositivo == "cuda":
            self._modelo = self._modelo.cuda()
        self._modelo.eval()

    def _transcribir(self, wav: str) -> str:
        salida = self._modelo.transcribe([wav])
        primero = salida[0]
        return getattr(primero, "text", primero)


# ---------------------------------------------------------------------------
# Voxtral Mini 3B (Mistral) - modelo de audio+texto; entiende contexto, asi que
# suele acertar mejor los anglicismos y nombres propios tecnicos.
# ---------------------------------------------------------------------------
class VoxtralMini(Motor):
    nombre = "voxtral-mini-3b"
    descripcion = "Mistral Voxtral Mini 3B en modo transcripcion"
    paquetes = ("torch", "transformers", "mistral_common")

    modelo_id = "mistralai/Voxtral-Mini-3B-2507"

    def cargar(self) -> None:
        import torch
        from transformers import AutoProcessor, VoxtralForConditionalGeneration

        self._procesador = AutoProcessor.from_pretrained(self.modelo_id)
        self._modelo = VoxtralForConditionalGeneration.from_pretrained(
            self.modelo_id,
            torch_dtype=torch.bfloat16,
            device_map=self.dispositivo,
        )

    def _transcribir(self, wav: str) -> str:
        entradas = self._procesador.apply_transcrition_request(
            language="es", audio=wav, model_id=self.modelo_id
        )
        entradas = entradas.to(self.dispositivo, dtype=self._modelo.dtype)
        salida = self._modelo.generate(**entradas, max_new_tokens=500)
        return self._procesador.batch_decode(
            salida[:, entradas.input_ids.shape[1] :], skip_special_tokens=True
        )[0]


# ---------------------------------------------------------------------------
# whisper.cpp via pywhispercpp - el plan B ligero: no depende de torch ni CUDA,
# arranca en milisegundos y no reserva VRAM. Util si el dictado va a estar
# residente todo el dia mientras entrenas otra cosa en la GPU.
# ---------------------------------------------------------------------------
class WhisperCpp(Motor):
    nombre = "whisper.cpp-turbo"
    descripcion = "whisper.cpp (GGML), residente barato en CPU"
    paquetes = ("pywhispercpp",)

    modelo_id = "large-v3-turbo-q5_0"

    def cargar(self) -> None:
        from pywhispercpp.model import Model

        self._modelo = Model(self.modelo_id, language="es", print_realtime=False)

    def _transcribir(self, wav: str) -> str:
        return " ".join(s.text for s in self._modelo.transcribe(wav))


# ---------------------------------------------------------------------------

REGISTRO: dict[str, type[Motor]] = {
    m.nombre: m
    for m in (
        WhisperTransformers,
        WhisperLargeV3,
        FasterWhisper,
        FasterWhisperJerga,
        ParakeetTDT,
        Canary,
        VoxtralMini,
        WhisperCpp,
    )
}


def crear(nombre: str, dispositivo: str = "cuda") -> Motor:
    if nombre not in REGISTRO:
        raise KeyError(f"motor desconocido: {nombre}. Hay: {', '.join(REGISTRO)}")
    return REGISTRO[nombre](dispositivo)


def inventario() -> list[tuple[str, bool, str, str]]:
    """(nombre, disponible, motivo si no, descripcion) para cada motor."""
    filas = []
    for nombre, clase in REGISTRO.items():
        ok, motivo = clase().disponible()
        filas.append((nombre, ok, motivo, clase.descripcion))
    return filas


if __name__ == "__main__":
    print(f"{'motor':<24} {'estado':<28} descripcion")
    print("-" * 100)
    for nombre, ok, motivo, desc in inventario():
        estado = "disponible" if ok else f"no ({motivo})"
        print(f"{nombre:<24} {estado:<28} {desc}")
