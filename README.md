# Veu

Dictado por voz global en Windows, local y con el motor de reconocimiento
intercambiable. Pulsas un atajo, hablas, y el texto aparece en el campo que
tenga el foco — sea Claude Code, el navegador o un terminal.

Este repo va en dos fases: primero se elige motor con datos, después se
construye el dictado.

## Dónde vive todo

`C:` estaba al límite (2,6 GB libres) y la primera instalación de torch murió
con `OSError: [Errno 28]`. Por eso **el venv y los modelos viven en `D:\Veu`**,
y en `C:` solo queda el código. `preparar_disco.ps1` monta ese entorno y, de
paso, redirige `PIP_CACHE_DIR` y `TMP` a `D:` — si no, pip cachea en `C:` el
wheel de 2,7 GB de torch y vuelve a llenarlo.

No se tocó la caché de HuggingFace de `C:` (50 GB), de la que dependen esdrac
y Balùa. Sigue pendiente decidir qué hacer con ella: `C:` sigue justo.

Dos cosas resueltas por el camino:

- **Parakeet no necesita NeMo.** `transformers` lo soporta nativo
  (`ParakeetForCTC` / `ForRNNT` / `ForTDT` y el pipeline de ASR). Canary sí lo
  exige, y por eso queda marcado como viable solo desde WSL.
- El corpus se puede sintetizar con SAPI para probar la tubería sin grabar.

## Fase 1 — Banco de pruebas

La premisa: los benchmarks públicos de ASR están medidos casi siempre con
inglés de locutor y audio limpio. Nada de eso predice cómo transcribe **tu**
voz, en tu micro, diciendo "Gradle", "versionCode" o "Artà". Así que se mide
con tu propia voz.

```powershell
.\activar.ps1               # venv en D:\Veu y HF_HOME apuntando allí

python grabar.py            # lees 20 frases, se guardan en grabaciones\
python evaluar.py --listar  # qué motores tienes instalados
python evaluar.py           # compara todos y escribe informe.md
```

Para comprobar que la tubería funciona **sin grabar nada**, hay un atajo que
sintetiza el corpus con el TTS de Windows (voz Helena, española):

```powershell
python sinteticas.py
python evaluar.py --grabaciones grabaciones_sinteticas --sufijo sintetico
```

Sirve para verificar que cada motor carga y devuelve texto. **No sirve para
elegir motor**: una voz sintética es limpia y monótona, así que el WER sale
optimista y no predice nada sobre tu voz real.

`evaluar.py` mide tres cosas:

| métrica | qué dice |
|---|---|
| **WER** | errores de palabra sobre la referencia — la calidad bruta |
| **WER llano** | lo mismo ignorando tildes y mayúsculas — cuánto del error es solo ortografía |
| **RTF** | segundos de cómputo por segundo de audio — la latencia que vas a notar |

La tabla dice cuál gana. `informe.md` dice **en qué** falla cada uno, que es
lo que realmente decide: un motor con 8 % de WER que siempre acierta los
nombres técnicos es mejor para dictar que uno con 6 % que escribe "Gradel".

## Resultados con voz sintética (27-jul-2026)

Prueba de humo sobre el corpus generado con SAPI, **no sirve para decidir**:
falta la voz real. Pero confirma que la tubería funciona y deja dos hallazgos.

| motor | WER útil | WER | RTF | s/frase |
|---|---|---|---|---|
| **faster-whisper-jerga** | **8,4 %** | 12,2 % | 0,05 | 0,23 |
| whisper-large-v3-hf | 12,2 % | 15,2 % | 0,25 | 1,10 |
| whisper-turbo-hf | 12,7 % | 16,0 % | 0,07 | 0,31 |
| whisper.cpp-turbo | 12,7 % | 16,0 % | 3,64 | 15,98 |
| faster-whisper-turbo | 13,1 % | 16,5 % | 0,17 | 0,75 |
| parakeet-tdt-0.6b-v3 | 15,6 % | 18,1 % | 0,04 | 0,15 |

**1. Sesgar el vocabulario vale más que cambiar de modelo.** El mismo
faster-whisper pasa de 13,1 % a 8,4 % solo pasándole tu jerga como
`initial_prompt`. Sin él, `keystore` sale como *"que historie"* y `Compose`
como *"CampoUS"*. Es la mejora más barata que hay y bate incluso a `large-v3`.

**2. Whisper traduce el mallorquín; Parakeet no.** Con `language="es"`, la
frase *"Bon dia, avui he d'anar a Artà a comprar el pa"* sale de Whisper como
*"Buen día, hoy voy a comprar el pan"* — traducida, no transcrita. Parakeet la
destroza pero al menos la deja en su idioma. Si vas a dictar en mallorquí hay
que resolverlo (detección automática o `language="ca"`), y eso es una decisión
de diseño de la fase 2, no un fallo del modelo.

Anotaciones sueltas: `faster-whisper` **sí funciona en Blackwell** (CTranslate2
trae kernels sm_120, el riesgo que temíamos no existe); y `whisper.cpp` da
calidad idéntica al turbo pero con RTF 3,64 — inservible para dictado tal como
está configurado, habría que fijarle `n_threads`.

## Motores candidatos

Todos en `motores.py`, todos detrás de la misma interfaz. Ninguno es
obligatorio: `evaluar.py` salta los que no tengas instalados.

| motor | por qué está en la lista |
|---|---|
| `whisper-turbo-hf` | el punto de referencia; buen español y va seguro en Blackwell vía torch cu128 |
| `whisper-large-v3-hf` | el Whisper completo: más preciso, bastante más lento |
| `faster-whisper-turbo` | el Whisper más rápido *si* CTranslate2 soporta sm_120; si no, cae a CPU |
| `parakeet-tdt-0.6b-v3` | NVIDIA, 600M parámetros y multilingüe; el candidato serio a ganar por latencia |
| `canary-1b-v2` | NVIDIA, multilingüe con puntuación y mayúsculas nativas |
| `voxtral-mini-3b` | Mistral; al ser modelo audio+texto entiende contexto y suele clavar anglicismos |
| `whisper.cpp-turbo` | plan B: no toca la VRAM, útil si el dictado vive residente mientras entrenas |

Añadir uno nuevo son ~15 líneas: hereda de `Motor`, declara sus paquetes,
implementa `cargar()` y `_transcribir()`, y regístralo en `REGISTRO`.

## Fase 2 — El dictado (pendiente)

Atajo global push-to-talk → graba mientras mantienes pulsado → transcribe con
el motor ganador → inyecta el texto en el input enfocado.

Dos decisiones ya tomadas:

- **Inyección por portapapeles + Ctrl+V**, no simulando pulsaciones. Es lo
  único fiable en todas las apps, incluidas Electron y los terminales. Se
  guarda y restaura el portapapeles anterior.
- **El atajo no será Win+Espacio tal cual** si resulta peleón: el shell se
  queda ese atajo para cambiar de idioma. Con AutoHotkey v2 (`#Space::`) se
  puede secuestrar limpiamente; si no, `Ctrl+Win+Espacio`.
