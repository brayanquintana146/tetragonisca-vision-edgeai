# Pendientes — tetragonisca-vision-edgeai

Última actualización: 4 de octubre de 2026. Rama: `feature/algoritmo-conteo`.

Lo hecho hasta ahora está en el [README](../README.md) (historial del modelo y validación del conteo) y en [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md) (contador híbrido y cómo se evalúa).

## Estado de partida

- **Video de prueba:** `0040-1`, con 36 entradas y 78 salidas anotadas en `data/gt_0040-1.csv`. No se usa para entrenar.
- **Modelo base para comparar:** `models/fomo_tetragonisca_int8.lite`, que nunca vio el `0040-1`.
- **Edge Impulse (proyecto 1108884):**
  - La versión **v4** guarda el estado con los 196 despegues del `0040-1`.
  - Esos 196 se borran del proyecto; deben quedar 1,595 muestras más las borrosas.
  - Se subieron **273 frames con abejas borrosas** de 44 videos de la colmena 004, sin el `0040-1` ni el `00427-28`.
  - Los frames de los videos 1.º, 8.º, 15.º, 22.º, 29.º y 36.º de la carpeta van a *test*.

## Pendientes (en orden)

### 1. Etiquetar las imágenes borrosas en Edge Impulse

- Poner caja `Abeja` a **todas** las abejas del frame, nítidas y borrosas. Una abeja sin caja le enseña al modelo que eso "no es abeja".
- La mancha alargada de una abeja en vuelo también lleva caja, centrada en la mancha. Usar la misma etiqueta `Abeja`, no una clase nueva.
- Corregir las cajas verdes pre-etiquetadas y borrar las que no sean abejas.
- Si alguien ayuda (*Dashboard → Collaborators*), repartirse por video y revisar al final una muestra de sus imágenes.

### 2. Entrenar el modelo nuevo (resolución 320)

1. *Object detection* con la misma configuración de siempre (README, sección 7).
2. Anotar las métricas de *Training* y de *Model testing*. El test ahora incluye abejas borrosas de 6 videos que el modelo no vio.
3. Guardar la versión: `v5 - sin 0040-1 + 273 borrosas de 44 videos (320)`.
4. Descargar el TFLite int8 como `models/fomo_borrosas_320_int8.lite`.

### 3. (Opcional) Entrenar con resolución 480

1. En *Impulse design → Image data*, cambiar 320×320 por 480×480.
2. Ir a *Generate features* y entrenar.
3. Descargar el modelo como `models/fomo_borrosas_480_int8.lite`.
4. Medir los FPS en la Raspberry Pi antes de adoptarlo: hace ~2.25 veces más cálculo.

### 4. Medir con el minuto completo del `0040-1`

```powershell
python main.py --video examples/videos/0040-1.mp4 --model models/fomo_tetragonisca_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.6 --max-gate-tentative 1.2 --accel-std 80 --no-output --events ev_base.csv
python main.py --video examples/videos/0040-1.mp4 --model models/fomo_borrosas_320_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.6 --max-gate-tentative 1.2 --accel-std 80 --no-output --events ev_A.csv
python bench/compare_events.py data/gt_0040-1.csv ev_base.csv ev_A.csv --tol 0.5 --max-angle 40 -q
python bench/detection_at_events.py --model models/fomo_borrosas_320_int8.lite
```

- Comparar siempre el F1 con la columna **F1 azar**.
- Meta: que suban las salidas acertadas y el % de salidas vistas por el detector, que hoy es 58% con `--crop-roi`.
- Si mejora, decidir si `--crop-roi --counter hibrido` y los ajustes pasan a ser los valores por defecto de `main.py`, y probar el modelo en la Raspberry Pi.

### 5. Preparar la presentación

- **Qué funciona:** las entradas (F1 claramente sobre el azar) y el detector con abejas nítidas (F1 0.93 en *Model testing*).
- **Qué funciona a medias:** las salidas, con la causa medida (abejas borrosas al despegar) y el efecto del reentrenamiento (paso 4).
- **Método:** la medición estricta con comparación contra el azar, el test separado por video y el video de prueba anotado a mano.
- **Trabajo futuro:**
  - cámara C930e con exposición fija (`deployment.md`, sección 5);
  - prueba de generalización: entrenar sin la colmena 004 y medir con el `0040-1`;
  - etiquetar pocas imágenes en la colmena final de Cusco.

## Otros pendientes

- **Rotar las API keys de Edge Impulse:** se compartieron dos (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys* y no dejar keys Admin activas.
- **Anotar un segundo video de prueba** con `tools/anotar_eventos.py`. Un solo minuto no basta para confirmar ajustes finos.
- **Prueba real con la webcam C930e en la Pi:**
  - fijar la exposición con `v4l2-ctl`;
  - calibrar la ROI con `--snapshot-every`;
  - grabar un clip y anotarlo.
- **Orden del repositorio:**
  - quitar la contraseña de `pi` y del Wi-Fi de `deployment.md` y cambiarla en la Pi;
  - licencia inconsistente (MIT en el badge, BSD 3-Clause en el repo);
  - revisar `output_result.mp4` y `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`;
  - `bench/make_scenarios.py` necesita TensorFlow como respaldo en Windows.
