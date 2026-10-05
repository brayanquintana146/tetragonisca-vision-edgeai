# Arquitectura de Seguimiento y Conteo (Tracking & Counting Algorithm)

> El sistema tiene dos versiones: **v2** (por defecto, `--tracker v2`) y **v1** (`--tracker v1`, EuTrack original, descrito más abajo). v2 nació porque v1 dejaba de contar las salidas cuando la entrada era una webcam y no el archivo de video.

## Tracker v2: independiente de la resolución y de los FPS

### Por qué v1 fallaba con la webcam
Los parámetros de v1 estaban fijados en **píxeles de un video 1920×1080** y en **frames de un video a 60 fps**. Con una webcam a 640×480 procesada a pocos FPS reales:

| Parámetro v1 | Pensado para 1080p @60 | Efecto en 640×480 @15 |
| :--- | :--- | :--- |
| `merge_radius = 60 px` | ~1 abeja | Fusiona varias abejas de la piquera en un solo punto |
| `max_distance = 250 px` | 13% del ancho | 40% del ancho: los IDs saltan entre abejas lejanas |
| `max_disappeared = 20 frames` | 0.33 s | 1.3 s de "fantasmas" que roban detecciones nuevas |
| `history_len >= 5` para inferir | 0.08 s | 0.33 s: una salida rápida nunca llega a 5 frames |

Además, el umbral `max_distance` se aplicaba **después** del Algoritmo Húngaro. Por eso, pares imposibles podían desplazar a pares válidos en la asignación.

### Qué cambia en v2 (`src/tracker.py::BeeTracker`, `src/counter.py::BeeCounterV2`)
1. **Unidades físicas:** todas las distancias se expresan en radios de la ROI y los tiempos en segundos (con el `dt` real entre frames). Los mismos parámetros sirven en 1080p y en 640×480, a 60 fps o a 10 fps.
2. **Filtro de Kalman de velocidad constante:** reemplaza el suavizado exponencial, que se quedaba atrás cuando la abeja aceleraba. La incertidumbre del filtro crece mientras la abeja no se ve.
3. **Gating antes del Húngaro:** cada track solo compite por las detecciones dentro de su ventana, de 3σ de su predicción (limitada a 0.35–1.2 radios).
4. **Tracks tentativos:** una detección aislada (reflejo, ruido de la pantalla) necesita 2 detecciones para convertirse en un ID.
5. **Doble umbral:** una detección débil (≥ 0.35, típica de una abeja borrosa) puede continuar un track existente. Solo una fuerte (≥ 0.55) crea uno nuevo.
6. **Conteo origen-destino:** una salida es un track que **nació dentro** de la ROI y **terminó fuera**, y una entrada es lo contrario. Si FOMO pierde la abeja al despegar o la detecta recién al aterrizar, se proyecta su posición con la velocidad del Kalman durante 0.25 s. Las guardianas que oscilan en el borde nacen y mueren del mismo lado, así que no cuentan.
7. **Captura en vivo:** la cámara se lee en un hilo aparte y siempre se procesa el frame más reciente, con su hora real de captura. Así no se acumulan frames viejos en el buffer.

### Contador híbrido (`--counter hibrido`, `src/counter.py::BeeCounterHybrid`)

**Problema de `BeeCounterV2`:** cuenta como máximo un evento por track. En la piquera hay tracks que duran 10–20 s: se quedan pegados a una guardiana y saltan a la abeja que despega. Cuando esa abeja sale, el track ya contó algo o termina dentro de la ROI, y la salida se pierde.

**Solución:**
- **Salidas por cruce (`BeeCounterCross`):** cada track lleva su lado actual (dentro/fuera, con histéresis de 0.15 r). Cada paso de dentro a fuera es una salida candidata. Si el track vuelve a cruzar antes de `--cancel-s` (0.5 s), se anulan los dos cruces: es una abeja que se asomó. Al cerrarse el track se proyecta su posición con la velocidad del Kalman, solo si va a más de `--proj-min-speed` (1.5 r/s).
- **Entradas como `BeeCounterV2`:** una por track y sin proyectar hacia atrás el nacimiento. Contar cada cruce hacia dentro sumaba entradas falsas de guardianas que caminan por el borde.

**Ajustes del tracker que lo acompañan:**
- `--max-gate 0.6`: un track confirmado solo acepta detecciones a menos de 0.6 radios de su predicción, así salta menos entre abejas vecinas.
- `--max-gate-tentative 1.2`: un track nuevo puede enlazar saltos grandes de una abeja en vuelo rápido.
- `--accel-std 80`: el Kalman acepta aceleraciones bruscas, como las de un despegue.

Los valores por defecto de `main.py` no cambian (`--counter v2`, `--max-gate 1.2`, `--accel-std 40`).

### Salidas fugaces (`--flash-exits`, `src/counter.py::FlashExits`)

**Problema:** al revisar una por una las 78 salidas del `0040-1` con el modelo 480, la abeja que despega aparece como una mancha borrosa fuera de la piquera en solo 1–2 frames, a unos 250 px entre uno y otro. El tracker pide dos detecciones seguidas con confianza ≥ `--threshold` para crear un ID, así que esa salida no se contaba. Además, 43 de las 80 salidas contadas eran falsas, sobre todo por proyectar fuera de la ROI tracks que se pierden cerca del borde.

**Regla:**
1. Una detección entre 1.0 y 2.5 radios del centro que no está a menos de 0.4 radios de una abeja rastreada en ese frame es candidata.
2. Las candidatas se enlazan en trazos (hasta 0.04 s entre una y otra, hasta 84 radios/s).
3. Un trazo de 3 detecciones o menos que no se acerca a la piquera es una salida, con el tiempo y la posición de su primera detección.
4. Se descarta si el contador de cruces ya contó una salida a menos de 0.4 s y 40°. Por eso cada salida se decide 1.5 s después.
5. Con esta opción se apaga la proyección de las salidas al cerrarse un track.

**Resultado** (minuto completo del `0040-1`, modelo 480, medición estricta, mismos ajustes del tracker):

| | Bien / contadas | Reales | F1 | F1 azar |
|---|---|---|---|---|
| Sin `--flash-exits` | 37 / 80 | 78 | 0.47 | 0.27 |
| Con `--flash-exits` | 49 / 65 | 78 | 0.69 | 0.39 |

Las entradas no cambian (F1 0.87). Con las detecciones del modelo v4 sube de 0.52 a 0.58. La regla se diseñó con este mismo minuto y a 60 fps: falta confirmarla con otro video anotado y revisar `max_hits` y `max_gap_s` a los 30 fps de la C930e.

### Cómo se evalúa el conteo

Se compara evento por evento contra `data/gt_0040-1.csv` con `bench/compare_events.py`. Hay dos cuidados importantes:

1. **Medición estricta:** `--tol 0.5 --max-angle 40`. Con ±1 s y solo por tiempo, eventos al azar a la misma tasa ya dan F1 ≈ 0.65 en salidas, porque hay ~1.3 salidas por segundo. En los eventos acertados de verdad, la diferencia de tiempo mediana es de 0.02 s.
2. **Comparar con el azar:** la columna *F1 azar* desplaza en el tiempo los mismos eventos del tracker. Un ajuste solo cuenta si mejora claramente sobre ella.

**Resultado con el modelo v4 + `--crop-roi`** (30–60 s, medición estricta, detecciones del PC):

| Contador | F1 IN (azar) | Salidas acertadas | F1 OUT (azar) |
| :--- | :---: | :---: | :---: |
| `v2` por defecto | 0.64 (0.26) | 6 de 38 | 0.22 (0.15) |
| `hibrido` + ajustes de arriba | 0.58 (0.23) | 18 de 38 | 0.46 (0.26) |

**Límite actual:** se barrieron más de 150 combinaciones (`--max-gate`, `--max-gate-tentative`, `--accel-std`, `--cancel-s`, `--proj-min-speed`, umbral de nacimiento), sobre las detecciones del PC y de Linux y con ruido simulado. El F1 de salidas no supera ~0.5–0.6. Solo `--accel-std 260 --max-gate-tentative 1.0` sube las entradas, de 0.58 a ~0.8 en 30–60 s, pero cuenta 58 salidas donde hay 38. El cuello de botella ya no es el tracker: FOMO deja de ver a la abeja borrosa al despegar. La siguiente mejora es reentrenar con abejas en vuelo (`scripts/05_extraer_borrosas.py`).

**Herramientas:**
- `bench/dump_detections.py`: guarda las detecciones crudas por frame en un `.json.gz`.
- `bench/replay_detections.py`: corre el tracker y el contador sobre ese archivo en segundos, con los mismos flags que `main.py`.

### Resultados en el banco de pruebas (`bench/`)
Se usan las detecciones reales de FOMO sobre `0040-1.mp4` y una simulación de webcam 640×480 filmando un monitor.

> **Corrección:** esta tabla se calculó contra 42 IN / 42 OUT, que salió de una lectura equivocada del paper. La columna RD de su Tabla 1 es la salida de sus algoritmos, no un conteo real. La referencia publicada es *Pseudo*: **42 IN / 85 OUT**, y probablemente incluye cruces de guardianas. Además, entre PC y Raspberry Pi solo ~55-65% de los eventos coinciden. La tabla sirve para comparar la robustez de v1 y v2 ante resolución y FPS, **no** como medida de exactitud. La exactitud se medirá evento por evento contra una anotación manual (`tools/anotar_eventos.py` + `bench/compare_events.py`).

```
Referencia de campo: 42 IN / 42 OUT. Promedio ± desv. sobre fases del submuestreo.
Escenario                    | v1:    IN          OUT       err | v2:    IN          OUT       err
video 1080p @60              | v1:  39.0±0.0  53.0±0.0  14.0 | v2:  40.0±0.0  42.0±0.0   2.0
video 1080p @30 (skip2)      | v1:  35.0±0.0  26.0±2.0  23.0 | v2:  38.0±4.0  36.0±3.0  10.0
webcam 640x480 @15           | v1:   6.5±1.5   4.5±2.5  73.0 | v2:  39.5±0.5  38.0±2.0   6.5
webcam @15 + jitter 25%      | v1:   5.7±1.0   4.3±1.0  74.0 | v2:  37.6±5.5  47.1±5.2  12.5
webcam @10                   | v1:   4.3±1.2   5.3±1.7  74.3 | v2:  38.7±2.4  63.0±4.2  24.3
webcam oscura @7.5           | v1:   2.5±0.5   5.0±1.0  76.5 | v2:  29.0±0.0  64.5±4.5  35.5
Error medio total (|IN-42|+|OUT-42|): v1=335, v2=91
```

**Limitaciones:**
- Los parámetros por defecto de v2 se ajustaron sobre este mismo video, así que hay riesgo de sobreajuste. Hay que validarlos con grabaciones reales de la cámara.
- Por debajo de ~10 fps efectivos las salidas se sobrecuentan. Una abeja que despega queda en 0–1 frames y la dirección se vuelve ambigua. La recomendación es mantener ≥ 15 fps efectivos.

---

## Tracker v1 (EuTrack)

El análisis del flujo de abejas en la piquera de *Tetragonisca angustula* presenta desafíos únicos para la visión por computadora: las abejas se cruzan constantemente a altas velocidades, oscilan o revolotean en la entrada sin decidirse a salir, y pueden aparecer borrosas debido a la limitación de cuadros por segundo de la cámara.

Para abordar esto, el sistema implementa un **Pipeline de Seguimiento y Conteo Adaptativo**.

### 1. Algoritmo de Asociación Global (Algoritmo Húngaro)
El principal problema al rastrear enjambres es el "ID Switching" (intercambio de identidades). Los enfoques que emparejan los centroides más cercanos por distancia euclidiana presentan limitaciones cuando dos o más abejas se cruzan, intercambiando las identidades y afectando las trayectorias.

Para resolver esto, se utiliza el **Algoritmo Húngaro** (`scipy.optimize.linear_sum_assignment`). Este algoritmo analiza una matriz de distancias globales entre todas las posiciones predichas y las nuevas detecciones en cada fotograma. En lugar de buscar la solución más óptima para la primera abeja, encuentra la asignación matemática que minimiza la distancia total del sistema, garantizando que los cruces y aglomeraciones no rompan las trayectorias individuales.

### 2. Cinemática Predictiva y Suavizado Adaptativo
Debido a la velocidad del vuelo de las Jataí, las detecciones por fotograma pueden estar muy distanciadas.

- **Predicción Vectorial de Velocidad:** Cuando FOMO falla en detectar una abeja durante uno o más fotogramas (micro-oclusión o desenfoque por movimiento rápido), el rastreador no congela su posición. En su lugar, avanza la posición esperada utilizando el último vector de velocidad válido conocido.
- **Amortiguación Fuerte:** Si una abeja desaparece repentinamente (ej. entra rápido al tubo), su velocidad predictiva se amortigua (se reduce al 40% en cada frame fantasma). Esto evita que el tracker "proyecte" trayectorias erróneas fuera del campo visual.
- **Suavizado Adaptativo (Alpha):** La interpolación entre la predicción y la nueva detección varía según la velocidad real de la abeja. Si la abeja camina lento, el suavizado es alto (trayectorias firmes); si vuela rápido, el suavizado es bajo (el tracker reacciona rápido para no quedarse atrás de la detección visual).

### 3. Lógica de Conteo Anti-Oscilaciones (Regla de Evento Único)
Las abejas guardianas y forrajeras suelen exhibir patrones de vuelo oscilatorio en el borde del ROI (Region of Interest). Cruzan la línea hacia afuera y hacia adentro repetidamente antes de decidir volar o aterrizar, inflando artificialmente los sistemas de conteo tradicionales.

Para neutralizar este fenómeno, se aplica una **lógica de bloqueo por ID**:
- Existe un conjunto en memoria de estado definitivo (`self.counted = set()`).
- En cuanto un ID registrado cruza la línea por primera vez (ya sea de adentro hacia afuera o viceversa), se incrementa el contador correspondiente y el ID queda registrado permanentemente.
- Cualquier cruce posterior de esa misma abeja a lo largo del límite, sin importar si cambia de dirección, **se ignora por completo**. Solo un desplazamiento continuo, la pérdida total de visibilidad y el reingreso eventual con un nuevo ID restablecerá la posibilidad de un nuevo conteo.

### 4. Conteo Inferido Vectorialmente para Vuelos Veloces
Las Jataí que salen de la colmena suelen acelerar muy rápido desde el tubo hasta fuera del campo de visión. FOMO logra detectarlas en la base del ROI, pero a menudo se pierden antes de que su centroide cruce visiblemente la línea límite, perdiendo un conteo de "SALIDA (OUT)".

El sistema incorpora un **Conteo Inferido por Desaparición**:
- Cuando una abeja cruza el umbral de `max_disappeared` y el tracker la elimina oficialmente, se revisa su último instante *activo*.
- Si la trayectoria duró lo suficiente para descartar ruido temporal (`history_len >= 5`) y nunca fue contabilizada de forma directa por cruce visible, se examina su vector de velocidad final.
- Si el vector de velocidad apunta matemáticamente **hacia afuera** de la circunferencia del ROI en el momento de desaparecer, el sistema infiere un cruce exitoso e incrementa las Salidas (OUT). Lo mismo se aplica a las entradas en ángulo ciego (IN).
