# Comparativa de motores ASR

`WER util` es la metrica que manda: ignora tildes y cuenta como
acierto que el motor escriba `45` donde dijiste *cuarenta y cinco*.

| motor | WER util | WER | WER llano | RTF | s/frase |
|---|---|---|---|---|---|
| whisper-large-v3-hf | **12.2%** | 15.2% | 14.8% | 0.25 | 1.10 |
| whisper-turbo-hf | **12.7%** | 16.0% | 15.2% | 0.07 | 0.31 |
| whisper.cpp-turbo | **12.7%** | 16.0% | 15.2% | 3.64 | 15.98 |
| faster-whisper-turbo | **13.1%** | 16.5% | 15.6% | 0.17 | 0.75 |
| parakeet-tdt-0.6b-v3 | **15.6%** | 18.1% | 18.1% | 0.04 | 0.15 |

## whisper-large-v3-hf

**11.wav** (9/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Buen día, hoy voy a comprar el pan.

**06.wav** (6/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemma a Litergm usando el DSA P-Dynamic WAI-4E-IFP32.

**09.wav** (4/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el Bebop DN8N está devolviendo el course correcto.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**17.wav** (3/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con PIP y usa el entorno de Python 3.12.

**02.wav** (2/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el version code y lanza el script de publicar release.

**08.wav** (3/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070 Ti tiene 16 GB de RAM y eso limita el tamaño del batch.

**03.wav** (2/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con Lora se quedó sin Brahma las tres horas.

**04.wav** (2/13 errores)

- esperado: Compila el módulo actualizador y firma el APK con la keystore de producción.
- obtenido: Compila el módulo actualizador y firma el APK con la que historie de producción.

**19.wav** (1/11 errores)

- esperado: Genera las ilustraciones de los ejercicios de cardio en formato SVG.
- obtenido: Genera las ilustraciones de los ejercicios de cardio U en formato SVG.

**01.wav** (1/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en CampoUS que muestre el progreso de la ruta.

## whisper-turbo-hf

**11.wav** (8/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Buen día, abu y edéan ahora harta a comprar el pa.

**06.wav** (7/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemma Alitergim usando el Resapidynamic WAI-4 e IFP32.

**02.wav** (3/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el version code y lanza el script de publicar Reléase.

**17.wav** (4/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con PIP y usa el entorno de Paezan 3.12.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**08.wav** (3/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070 Ti tiene 16 GB de RAM y eso limita el tamaño del batch.

**09.wav** (2/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el Bebock de N8N está devolviendo el course correcto.

**16.wav** (2/11 errores)

- esperado: ¿Puedes revisar por qué el DataStore no persiste el anchor mode?
- obtenido: Puedes revisar por qué el Data Store no persiste el Anchor Mode.

**18.wav** (2/14 errores)

- esperado: Al final el problema no era el driver del wifi, era la memoria RAM.
- obtenido: Al final el problema no era el driver del Wi-Fi, era la memoria RAM.

**07.wav** (1/11 errores)

- esperado: Haz un commit con el mensaje arreglado el desbordamiento del contador.
- obtenido: Haz un camit con el mensaje Arreglado el desbordamiento del contador.

**19.wav** (1/11 errores)

- esperado: Genera las ilustraciones de los ejercicios de cardio en formato SVG.
- obtenido: Genera las ilustraciones de los ejercicios de cardio U en formato SVG.

**03.wav** (1/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con Lora se quedó sin Brahma a las tres horas.

**01.wav** (1/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en Campus que muestre el progreso de la ruta.

## whisper.cpp-turbo

**06.wav** (8/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemma Alitergim usando el D-SAPI Dynamic WAI-4E y FP32.

**11.wav** (6/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Buen día, abu y de anar a harta a comprar el pa.

**02.wav** (3/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el version code y lanza el script de publicar Reléase.

**17.wav** (4/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con pip y usa el entorno de Paezan 3.12.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**08.wav** (3/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070 Ti tiene 16 GB de RAM y eso limita el tamaño del batch.

**09.wav** (2/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el Bebock de N8N está devolviendo el course correcto.

**16.wav** (2/11 errores)

- esperado: ¿Puedes revisar por qué el DataStore no persiste el anchor mode?
- obtenido: Puedes revisar por qué el Data Store no persiste el Anchor Mode.

**01.wav** (2/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en Campo US que muestre el progreso de la ruta.

**18.wav** (2/14 errores)

- esperado: Al final el problema no era el driver del wifi, era la memoria RAM.
- obtenido: Al final el problema no era el driver del Wi-Fi, era la memoria RAM.

**07.wav** (1/11 errores)

- esperado: Haz un commit con el mensaje arreglado el desbordamiento del contador.
- obtenido: Haz un camit con el mensaje arreglado el desbordamiento del contador.

**19.wav** (1/11 errores)

- esperado: Genera las ilustraciones de los ejercicios de cardio en formato SVG.
- obtenido: Genera las ilustraciones de los ejercicios de cardio U en formato SVG.

**03.wav** (1/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con Lora se quedó sin Brahma a las tres horas.

## faster-whisper-turbo

**06.wav** (8/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemma Alitergim usando el D-SAPI Dynamic WAI-4 e IFP32.

**11.wav** (8/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Buen día, abu y edéan ahora harta a comprar el pa.

**02.wav** (3/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el version code y lanza el script de publicar Reléase.

**17.wav** (4/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con PIP y usa el entorno de Paezan 3.12.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**08.wav** (3/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070 Ti tiene 16 GB de RAM y eso limita el tamaño del batch.

**09.wav** (2/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el Bebock de N8N está devolviendo el course correcto.

**16.wav** (2/11 errores)

- esperado: ¿Puedes revisar por qué el DataStore no persiste el anchor mode?
- obtenido: Puedes revisar por qué el Data Store no persiste el Anchor Mode.

**18.wav** (2/14 errores)

- esperado: Al final el problema no era el driver del wifi, era la memoria RAM.
- obtenido: Al final el problema no era el driver del Wi-Fi, era la memoria RAM.

**07.wav** (1/11 errores)

- esperado: Haz un commit con el mensaje arreglado el desbordamiento del contador.
- obtenido: Haz un kamit con el mensaje arreglado el desbordamiento del contador.

**19.wav** (1/11 errores)

- esperado: Genera las ilustraciones de los ejercicios de cardio en formato SVG.
- obtenido: Genera las ilustraciones de los ejercicios de cardio U en formato SVG.

**03.wav** (1/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con Lora se quedó sin Brahma a las tres horas.

**01.wav** (1/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en Campus que muestre el progreso de la ruta.

## parakeet-tdt-0.6b-v3

**06.wav** (7/11 errores)

- esperado: Quiero exportar Gemma a litertlm usando el recipe dynamic wi4 afp32.
- obtenido: Quiero exportar Gemmaliter Gim usando el Res API Dynamic WI4AFP32.

**11.wav** (6/12 errores)

- esperado: Bon dia, avui he d'anar a Artà a comprar el pa.
- obtenido: Bom dia, abuille de a Narta a comprar el pa.

**17.wav** (7/14 errores)

- esperado: Instala las dependencias con pip y usa el entorno de Python tres punto doce.
- obtenido: Instala las dependencias con Pipeus al entorno de Python 3.12.

**08.wav** (5/16 errores)

- esperado: La RTX 5070 Ti tiene dieciséis gigas de VRAM y eso limita el tamaño del batch.
- obtenido: La RTX 5070T tiene 16 GB de BRAM y eso limita el tamaño del batch.

**02.wav** (3/10 errores)

- esperado: Sube el versionCode y lanza el script de publicar release.
- obtenido: Sube el versión code y lanza el script de publicar RLAC.

**12.wav** (3/13 errores)

- esperado: El pipeline de datos tarda unos cuarenta y cinco minutos en procesarlo todo.
- obtenido: El pipeline de datos tarda unos 45 minutos en procesarlo todo.

**09.wav** (2/11 errores)

- esperado: Mira si el webhook de n8n está devolviendo el CORS correcto.
- obtenido: Mira si el bebog de N8N está devolviendo el course correcto.

**16.wav** (2/11 errores)

- esperado: ¿Puedes revisar por qué el DataStore no persiste el anchor mode?
- obtenido: Puedes revisar por qué el data store no persiste el anchor mode.

**01.wav** (2/13 errores)

- esperado: Añade una pantalla nueva en Compose que muestre el progreso de la ruta.
- obtenido: Añade una pantalla nueva en Campo Us que muestre el progreso de la ruta.

**04.wav** (2/13 errores)

- esperado: Compila el módulo actualizador y firma el APK con la keystore de producción.
- obtenido: Compila el módulo actualizador y firma el APK con la que histore de producción.

**18.wav** (2/14 errores)

- esperado: Al final el problema no era el driver del wifi, era la memoria RAM.
- obtenido: Al final el problema no era el driver del Wi-Fi, era la memoria RAM.

**07.wav** (1/11 errores)

- esperado: Haz un commit con el mensaje arreglado el desbordamiento del contador.
- obtenido: Haz un camit con el mensaje arreglado el desbordamiento del contador.

**03.wav** (1/12 errores)

- esperado: El entrenamiento con LoRA se quedó sin VRAM a las tres horas.
- obtenido: El entrenamiento con Lora se quedó sin Brahma a las tres horas.
