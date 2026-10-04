# Pendientes — tetragonisca-vision-edgeai

Última actualización: 4 de octubre de 2026. Rama: `feature/algoritmo-conteo`.

## Dónde quedamos

**Objetivo del conteo:** contar solo las abejas que **realmente entran** a la colmena o **se van**, sin guardianas ni abejas que se asoman y vuelven.

**Verdad de campo:** `data/gt_0040-1.csv`, anotada a mano en el minuto completo del video `0040-1`. Tiene **36 entradas y 78 salidas**. Como referencia, el conteo *Pseudo* del paper (Tabla 1) es 42 IN / 85 OUT / 156 abejas.

**Tracker v2 contra la anotación** (`bench/compare_events.py`, ±1 s):

| | Precisión IN | Recall IN | Precisión OUT | Recall OUT |
|---|---|---|---|---|
| PC (TensorFlow) | 0.65 | 0.83 | 0.80 | **0.45** |
| Raspberry Pi 5 (LiteRT) | 0.69 | 0.86 | 1.00 | **0.42** |

- **Entradas:** se detectan bien, pero sobran ~15, que probablemente son guardianas.
- **Salidas:** se pierde más de la mitad. En el momento del cruce, el modelo ve en 3 o más frames al **83%** de las abejas que entran, pero solo al **19%** de las que salen, porque ya van volando y salen borrosas. **El cuello de botella de las salidas es el detector (FOMO), no el tracker.**
- **Diferencias entre PC y Pi:** con el mismo código, cada runtime da conteos distintos (pequeñas diferencias numéricas del modelo int8). Solo ~55-65% de los eventos coinciden entre PC y Pi.

## Avance del 3–4 de octubre de 2026

- **Etiqueta unificada en Edge Impulse (punto 1, hecho).** La v3 (17 sep, 1,595 muestras) sirvió de respaldo porque el proyecto no había cambiado desde entonces. `tools/renombrar_etiqueta_ei.py` encontró 13,373 cajas `'Abeja\r'` en 1,391 muestras y las renombró a `'Abeja'`. Ahora hay **una sola clase**. Ojo: renombrar cajas pide una API key con rol **Admin**; la key de ingestión da error 403.
- **Despegues subidos y etiquetados (punto 2, pasos 1 y 2, hechos).** Se subieron las 196 imágenes de `data/despegues/train` a *training*. El `classes.txt` se revisó byte a byte: dice `Abeja`, sin `\r` ni salto de línea. Se corrigieron las pre-etiquetas y se agregaron las abejas en vuelo (manchas borrosas). El círculo magenta de `referencia/` está fijo en el punto anotado, así que en los frames −6/−3/+3/+6 la abeja puede estar fuera del círculo.
- **Versión guardada** en *Versioning*: "Modelo v3 + 196 imágenes de despegues etiquetadas".
- **Línea base del modelo viejo** generada en `eventos_v2.csv` (`main.py --events`), para comparar después.
- **Modelo reentrenado (punto 2, paso 3, hecho)** con la misma configuración. *Model testing*:

| | Accuracy test | Precisión | Recall | F1 |
|---|---|---|---|---|
| v3 (17 sep) | 96% | 1.00 | 0.88 | 0.93 |
| Nuevo, con despegues (4 oct) | 94.42% | 0.98 | 0.88 | 0.93 |

  Queda prácticamente igual con las abejas normales. Este test no mide los despegues; eso se mide en el paso 4 con el video.
- **Test en Edge Impulse:** los despegues van todos a *training* a propósito. El test real de despegues es la segunda mitad del video (`--start 30`). Si más adelante se quiere un test de despegues en Edge Impulse, se puede sacar de la segunda mitad del 0040-1 (hay que agregar esa opción a `04_extraer_despegues.py`).
- **Modelo nuevo contra el viejo** (PC, TensorFlow, segunda mitad del video): recall OUT 0.39 → 0.42 (15 → 16 de 38), precisión OUT 0.68 → 0.89, pero precisión IN 0.78 → 0.54 (13 entradas falsas, varias en los mismos puntos de la piquera). Casi no mejora las salidas. **No se reemplazó el modelo.**

## Pendientes (en orden)

### 1. ~~Unificar la etiqueta en Edge Impulse~~ — hecho el 3 de octubre

### 2. Reentrenar FOMO con abejas despegando (camino 1) — falta el paso 4

Pasos 1 a 3 hechos (ver *Avance* arriba). Si hay que regenerar `data/despegues/` (no va a GitHub):

```powershell
python scripts/04_extraer_despegues.py --gt data/gt_0040-1.csv --video examples/videos/0040-1.mp4 --split 30
```

**Siguiente:**

4. Descargar el modelo nuevo: Edge Impulse → *Dashboard* → *Download block output* → **TensorFlow Lite (int8 quantized)**. Guardarlo como `models/fomo_nuevo_int8.lite`, **sin reemplazar** `models/fomo_tetragonisca_int8.lite`.
5. Evaluar **solo la segunda mitad** del video, que el modelo no vio:
   ```powershell
   python main.py --video examples/videos/0040-1.mp4 --model models/fomo_nuevo_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --no-output --events eventos_nuevo.csv
   python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv eventos_nuevo.csv --start 30
   ```
   Meta: que el recall de OUT suba claramente de ~0.45 sin que baje la precisión.
6. Si mejora, reemplazar el modelo por defecto y probarlo también en la Raspberry Pi.

### 3. Rotar las API keys de Edge Impulse

Se compartieron dos keys (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys* y crear una nueva de ingestión para el uploader. No dejar keys Admin activas.


### 4. Pulir el tracker (camino 2)

Medir siempre con `bench/compare_events.py` contra `data/gt_0040-1.csv`.

- **Entradas falsas (~15):** casi todas caen en las mismas posiciones de la piquera. Probablemente son guardianas: exigir más evidencia para contar una entrada.
- **8 salidas contadas como entrada:** revisar la dirección que asigna el origen-destino y la proyección hacia atrás (`back_project`).
- **11 salidas con una sola detección:** evaluar crear tracks con 1 detección fuerte cerca del borde.
- **Estabilidad PC/Pi:** agregar al banco de pruebas ruido del tamaño de la diferencia entre runtimes y exigir que los eventos casi no cambien.

### 5. Preprocesamiento igual al del entrenamiento — opción `--crop-roi` agregada

Edge Impulse entrena con *Fit shortest axis* (recorte central), pero `main.py` aplasta el frame completo a 320×320, así que las abejas llegan deformadas. Ahora `main.py --crop-roi` recorta un cuadrado del lado corto del frame (1080×1080 en el video 0040-1) centrado en la ROI. Sin la opción, todo funciona igual que antes (verificado: mismos eventos).

Resultado con el modelo **viejo** (LiteRT en Linux, video completo):

| | Frame completo | `--crop-roi` |
|---|---|---|
| Detector: salidas vistas en ≥3 de 13 frames (`bench/detection_at_events.py`) | 41% | **54%** |
| Tracker: recall OUT (`compare_events.py`) | 0.49 | 0.37 |
| Tracker: recall IN | 0.83 | 0.89 |

Con el modelo **nuevo** (PC, TensorFlow, segunda mitad del video, 38 salidas):

| | Frame completo | `--crop-roi` |
|---|---|---|
| Detector: salidas vistas en ≥3 de 13 frames | 45% | **58%** |
| Tracker: recall OUT | 0.42 | 0.34 |
| Tracker: precisión IN | 0.54 | 0.62 |

Referencia, modelo viejo en la misma ventana (LiteRT): 37% sin recorte, 47% con recorte. **El reentrenamiento y el recorte sí ayudan al detector** (de ~37% a 58% de salidas vistas), pero el tracker pierde esas salidas. **El cuello de botella ahora es el tracker (punto 4).**

El **detector** ve más abejas saliendo con el recorte, pero el **conteo de salidas empeora**: los parámetros del tracker se ajustaron con el frame aplastado. Falta: (a) probar el modelo nuevo con `--crop-roi`, y (b) revisar por qué el tracker pierde esas salidas (punto 4).

### 6. Prueba real con la webcam (Logitech C930e en la Raspberry Pi)

- Fijar la exposición y apagar el autofoco con `v4l2-ctl` (sección 5 de `deployment.md`).
- Calibrar la ROI con `--snapshot-every` para la resolución de la cámara.
- Grabar un clip crudo con `ffmpeg -f v4l2 -input_format mjpeg -video_size 640x480 -framerate 30 -i /dev/video0 -t 70 -c copy clip_webcam.mkv` y anotarlo con `tools/anotar_eventos.py`, para evaluar con condiciones reales.

### 7. Orden y seguridad del repositorio

- **Contraseña expuesta:** `deployment.md` tiene escrita la contraseña del usuario `pi` y del Wi-Fi. Si el repo es público, quitarla y cambiarla en la Pi con `passwd`. Igual queda en el historial de git.
- **Licencia inconsistente:** el badge del README dice MIT, pero el árbol del repo dice BSD 3-Clause.
- **Árbol del README desactualizado:** faltan `src/`, `bench/`, `tools/`, `main.py` y `deployment.md`.
- **Archivos por revisar:** `output_result.mp4` (~33 MB) y la carpeta `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`, que parece temporal.
- **Windows:** `bench/make_scenarios.py` importa `ai_edge_litert`, que no existe para Windows. Adaptarlo para que use TensorFlow como respaldo, igual que `main.py`.

## Herramientas creadas

| Archivo | Para qué |
|---|---|
| `tools/anotar_eventos.py` | Anotar a mano entradas/salidas reales de un video (genera el CSV de verdad de campo) |
| `bench/compare_events.py` | Comparar eventos del tracker contra la anotación: TP/FP/FN, precisión y recall por tipo |
| `scripts/04_extraer_despegues.py` | Extraer frames alrededor de cada salida anotada, con pre-etiquetas, para reentrenar |
| `tools/etiquetar_cajas.py` | Editor local de cajas YOLO, con zoom sobre la abeja que despega |
| `tools/renombrar_etiqueta_ei.py` | Renombrar etiquetas de cajas en todo un proyecto de Edge Impulse vía API |
| `bench/make_scenarios.py` + `bench/run_bench.py` | Banco de pruebas con escenarios de webcam simulada (solo totales; referencia orientativa) |
| `test_tracker_v2.py` | Pruebas sintéticas del tracker v2 |
