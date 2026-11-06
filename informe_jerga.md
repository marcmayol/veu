# Comparativa de motores ASR

`WER util` es la metrica que manda: ignora tildes y cuenta como
acierto que el motor escriba `45` donde dijiste *cuarenta y cinco*.

| motor | WER util | WER | WER llano | RTF | s/frase |
|---|---|---|---|---|---|
| faster-whisper-jerga | **8.4%** | 12.2% | 11.4% | 0.05 | 0.23 |

## faster-whisper-jerga

**06.wav** (7/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemma Alitergim usando el D-SAPI Dynamic WAI-4E IFP32.

**11.wav** (5/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Bon dia, avui e de anara arta a comprar el pa.

**17.wav** (4/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con pip y usa el entorno de Paezan 3.12.

**03.wav** (3/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con LoRa se quedó sin Brahma las 3 horas.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**08.wav** (3/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070 Ti tiene 16 GB de RAM y eso limita el tamaño del batch.

**02.wav** (1/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el versionCode y lanza el script de publicar Reléase.

**09.wav** (1/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el BBVA de n8n está devolviendo el CORS correcto.

**19.wav** (1/11 errores)

- esperado: Genera las ilustraciones de los ejercicios de cardio en formato SVG.
- obtenido: Genera las ilustraciones de los ejercicios de cardio U en formato SVG.

**01.wav** (1/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en Campus que muestre el progreso de la ruta.
