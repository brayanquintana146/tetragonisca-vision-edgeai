# Pendientes — tetragonisca-vision-edgeai

Última actualización: 30 de septiembre de 2026. Rama: `feature/algoritmo-conteo`.

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

## Pendientes (en orden)

### 1. Unificar la etiqueta en Edge Impulse (`Abeja\r` → `Abeja`)

El dataset se subió con un `classes.txt` de Windows y las cajas quedaron como `Abeja\r`, con un retorno de carro invisible. Las cajas dibujadas a mano en Studio quedan como `Abeja`, así que aparecen dos clases. Los scripts `01_preparar_train.py` y `04_extraer_despegues.py` ya están corregidos y ahora escriben `Abeja` sin `\r`.

**Hay que hacer esto antes de subir cualquier cosa nueva:**

1. Edge Impulse → *Versioning* → *Store new version* (respaldo).
2. Ver qué etiquetas hay, sin cambiar nada:
   ```powershell
   $env:EI_API_KEY = "ei_..."        # Dashboard > Keys
   python tools/renombrar_etiqueta_ei.py --project-id 1108884
   ```
3. Si muestra `'Abeja\r'` (y quizá `'Abeja'`), aplicar el cambio:
   ```powershell
   python tools/renombrar_etiqueta_ei.py --project-id 1108884 --apply
   ```
4. Comprobar que al final solo quede `'Abeja'`.

### 2. Reentrenar FOMO con abejas despegando (camino 1)

**Estado:** los frames ya se extrajeron en `data/despegues/`: 196 imágenes de las 40 salidas anotadas antes del segundo 30, con pre-etiquetas del modelo actual. Se subieron a Edge Impulse **y luego se borraron** por el problema de la etiqueta del punto 1. Esa carpeta no va a GitHub; si falta, se regenera con:

```powershell
python scripts/04_extraer_despegues.py --gt data/gt_0040-1.csv --video examples/videos/0040-1.mp4 --split 30
```

**Pasos (después del punto 1):**

1. Subir: `edge-impulse-uploader --api-key TU_API_KEY --category training --directory data/despegues/train --dataset-format yolo-txt`
2. Etiquetar las 196 imágenes (en Edge Impulse, o en local con `python tools/etiquetar_cajas.py --dir data/despegues/train --gt data/gt_0040-1.csv` y volver a subir):
   - Agregar la caja de la **abeja que despega**. Está cerca del círculo magenta en `data/despegues/referencia/`.
   - Agregar cualquier otra abeja sin caja y borrar las cajas incorrectas.
   - Si ni uno distingue la abeja, no etiquetarla.
3. Reentrenar con la misma configuración (FOMO, MobileNetV2 0.35, 320×320). En *Model testing*, la precisión debe seguir cerca de 1.00. En *Object detection* debe decir **1 clase**.
4. Descargar el `.lite` nuevo a `models/` y evaluar **solo la segunda mitad** del video, que el modelo no vio:
   ```powershell
   python main.py --video examples/videos/0040-1.mp4 --roi-x 900 --roi-y 600 --roi-r 220 --no-output --events eventos_nuevo.csv
   python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv eventos_nuevo.csv --start 30
   ```
   Meta: que el recall de OUT suba claramente de ~0.45.

### 3. Pulir el tracker (camino 2)

Medir siempre con `bench/compare_events.py` contra `data/gt_0040-1.csv`.

- **Entradas falsas (~15):** casi todas caen en las mismas posiciones de la piquera. Probablemente son guardianas: exigir más evidencia para contar una entrada.
- **8 salidas contadas como entrada:** revisar la dirección que asigna el origen-destino y la proyección hacia atrás (`back_project`).
- **11 salidas con una sola detección:** evaluar crear tracks con 1 detección fuerte cerca del borde.
- **Estabilidad PC/Pi:** agregar al banco de pruebas ruido del tamaño de la diferencia entre runtimes y exigir que los eventos casi no cambien.

### 4. Preprocesamiento igual al del entrenamiento

Edge Impulse entrenó con *Fit shortest axis* (recorte central), pero `main.py` aplasta el frame completo a 320×320, así que las abejas llegan deformadas. Probar recortar un cuadrado alrededor de la ROI. En una prueba rápida, la detección de salidas en ≥3 frames subió de 19% a 28%.

### 5. Prueba real con la webcam (Logitech C930e en la Raspberry Pi)

- Fijar la exposición y apagar el autofoco con `v4l2-ctl` (sección 5 de `deployment.md`).
- Calibrar la ROI con `--snapshot-every` para la resolución de la cámara.
- Grabar un clip crudo con `ffmpeg -f v4l2 -input_format mjpeg -video_size 640x480 -framerate 30 -i /dev/video0 -t 70 -c copy clip_webcam.mkv` y anotarlo con `tools/anotar_eventos.py`, para evaluar con condiciones reales.

### 6. Orden y seguridad del repositorio

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
