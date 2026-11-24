# Guía para correr el conteo y entender sus parámetros

Esta guía explica cómo correr `main.py` en los casos más comunes y qué hace cada parámetro, en palabras simples. Para el detalle técnico y los números de cada regla, ver [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md). Para cómo se midieron los resultados, ver [VALIDACION.md](VALIDACION.md).

## 1. La idea en 30 segundos

En cada imagen del video pasan cuatro cosas, en este orden:

```text
1. Recorte   ─►  2. Detección  ─►  3. Seguimiento  ─►  4. Conteo
(--crop-roi)     (FOMO, --model)    (tracker, Kalman)    (círculo de la piquera)
```

1. **Recorte.** Se toma un cuadrado alrededor de la piquera y se reduce al tamaño que espera el modelo (480×480 en la v5).
2. **Detección.** El modelo FOMO divide la imagen en una grilla de celdas (60×60 en la v5) y da, para cada celda, la probabilidad de que haya una abeja. Las celdas vecinas con abeja se juntan en un solo punto: el centro de la abeja. FOMO no dibuja cajas, solo da centros. Por eso es tan liviano (54 KB).
3. **Seguimiento.** El tracker une los puntos de una imagen con los de la siguiente, para saber que "esta abeja es la misma de hace un instante". Usa un **filtro de Kalman**, que predice dónde estará cada abeja según su velocidad, y el **algoritmo Húngaro**, que reparte las detecciones entre las abejas de forma que la distancia total sea la menor posible.
4. **Conteo.** Sobre la piquera se dibuja un círculo amarillo. Una abeja que cruza de fuera hacia dentro es una **entrada**; de dentro hacia fuera, una **salida**. Varias reglas descartan lo que no es una entrada o salida real: guardianas que revolotean, abejas que se asoman y vuelven, y manchas del fondo que el modelo confunde con abejas.

### Dos unidades que conviene entender

- **Escala (en "radios").** Las distancias del tracker no se miden en píxeles, sino en múltiplos del radio del círculo (`--roi-r`) o de `--track-scale`. Así los mismos parámetros sirven en un video de 1920×1080 y en uno de 640×480.
- **Tiempo (en segundos).** Los tiempos se miden en segundos reales, no en imágenes. Así sirven igual a 60 fps (videos del dataset) y a 30 fps (cámara C930e).

## 2. Comandos listos para usar

En Windows, una línea larga se puede partir con `` ` `` al final de cada línea en PowerShell. Aquí se escribe todo en una línea para poder copiarla.

### a) Video de ejemplo, con la configuración recomendada

```powershell
python main.py --video examples/videos/0040-1.mp4 --model models/v5_fomo_borrosas_480_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --rep-s 60 --num-threads 4 --show --no-output --events eventos.csv
```

Resultado esperado: 32 entradas y 44 salidas. `--show` abre una ventana con el video a su velocidad real; se cierra con la tecla `q`.

Para guardar el video anotado, cambiar `--no-output` por `--output video_conteo.mp4`. Guardar video cuesta tiempo: en un PC de 4 núcleos el análisis baja de ~140 a ~40 imágenes por segundo, y la ventana se ve más lenta que el video real.

### b) Colmena que el modelo nunca vio

Igual que (a), cambiando el círculo para esa colmena y agregando las reglas contra manchas del fondo:

```powershell
python main.py --video VIDEO.mp4 --model models/v5_fomo_borrosas_480_int8.lite --roi-x X --roi-y Y --roi-r R --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --rep-s 60 --in-max-age 3 --in-park-s 0.15 --park-s 0.9 --events eventos.csv
```

Esta es la configuración que se usó en la prueba a ciegas. Antes, ubicar la piquera (ver sección 4).

### c) Cámara en vivo (PC o Raspberry Pi)

```powershell
python main.py --video 0 --cam-width 1280 --cam-height 720 --cam-fps 30 --model models/v5_fomo_borrosas_480_int8.lite --roi-x X --roi-y Y --roi-r R --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --rep-s 60 --no-output --show
```

En la Raspberry Pi: `--video /dev/video0`, `--num-threads 4` y, sin monitor, `--dashboard` en vez de `--show`. Sin `--cam-width` y `--cam-height`, Windows abre la cámara a 640×480 y el círculo puede quedar fuera de la imagen.

> La exactitud con la cámara en vivo a 30 fps todavía no está medida: los resultados publicados son con videos del dataset a 60 fps.

### d) Medir contra un conteo a mano

```powershell
python bench/compare_events.py data/gt_0040-1.csv eventos.csv --tol 0.5 --max-angle 40 --roi-x 900 --roi-y 600
```

Cada evento del programa debe coincidir con uno anotado a mano: mismo tipo, a menos de 0.5 s y del mismo lado de la piquera (±40°). Muestra precisión, recall, F1 y el F1 que daría contar al azar.

## 3. Parámetros, uno por uno

En cada tabla: **defecto** es el valor si no se escribe la opción; **recomendado** es el de la configuración de la sección 2.

### 3.1 Entrada y salida de archivos

| Opción | Defecto | Qué hace |
| :--- | :--- | :--- |
| `--video` | (obligatorio) | Archivo de video, o número de cámara (`0`) o `/dev/video0` en la Pi. |
| `--model` | `models/v3_...` | Modelo `.lite` a usar. Se recomienda `models/v5_fomo_borrosas_480_int8.lite`: es el que mejor detecta y el de los resultados publicados. |
| `--output` | `output_result.mp4` | Video con las anotaciones dibujadas. |
| `--no-output` | apagado | No guarda video. Ahorra tiempo y disco, sobre todo en la Pi. |
| `--events` | ninguno | CSV con una fila por cada entrada o salida: tiempo, tipo (IN/OUT), ID y posición. Es lo que se compara contra el conteo a mano. |
| `--log` | ninguno | CSV con una fila por imagen: totales acumulados y velocidad. |
| `--show` | apagado | Abre una ventana con el video anotado (solo en PC con pantalla). Con un video de archivo, lo muestra a su velocidad real: si el equipo analiza más rápido, espera; si analiza más lento, se ve en cámara lenta. |
| `--dashboard` | apagado | Página web con el conteo en vivo, en `http://IP:5000`. Sirve para ver la Pi desde el celular o la laptop. |
| `--snapshot-every N` | 0 (apagado) | Guarda una imagen anotada cada N imágenes en `--snapshot-dir` (por defecto `snapshots/`). Sirve para revisar sin pantalla. |

### 3.2 Cámara y velocidad

| Opción | Defecto | Qué hace |
| :--- | :--- | :--- |
| `--cam-width`, `--cam-height` | del driver | Resolución pedida a la cámara. Con la C930e: 1280 × 720. |
| `--cam-fps` | del driver | Imágenes por segundo pedidas a la cámara. La C930e llega a 30. |
| `--num-threads` | 1 | Núcleos del procesador para el modelo. Con 4 el modelo corre casi el doble de rápido y cuenta exactamente lo mismo. En la Pi 5 y en un PC: 4. |
| `--skip-frames N` | 1 | Analiza 1 de cada N imágenes. Acelera, pero una abeja que despega puede quedar en una sola imagen o en ninguna. Por debajo de ~15 imágenes por segundo efectivas las salidas se cuentan mal. Con cámara en vivo no se usa. |

### 3.3 El círculo de la piquera

| Opción | Defecto | Recomendado | Qué hace |
| :--- | :--- | :--- | :--- |
| `--roi-x`, `--roi-y` | 900, 640 | según el video | Centro del círculo, en píxeles. Va sobre la boca del tubo. |
| `--roi-r` | 200 | según el video | Radio del círculo, en píxeles. Cruzar ese borde es lo que cuenta como entrada o salida. |
| `--crop-roi` | apagado | **encendido** | Recorta un cuadrado centrado en la piquera antes de pasarlo al modelo, en lugar de aplastar toda la imagen. Así las abejas llegan al modelo con el mismo tamaño que en el entrenamiento. El cuadrado se dibuja en naranja. |
| `--core` | ninguno | 0.5 | La **boca** de la piquera: un círculo interior (magenta) de esa fracción del radio. Una salida solo cuenta si la abeja pasó por la boca; una entrada solo si llega a ella. Así no cuentan las guardianas que vuelan frente al tubo y cruzan el borde sin entrar. |
| `--track-scale` | = `--roi-r` | 220 si el círculo es chico | Tamaño de referencia que usa el tracker para medir distancias. Permite un círculo chico (para dejar fuera a las guardianas) sin que el tracker parta una abeja en dos. Ejemplo: `--roi-r 100 --track-scale 220`. |

**Por qué `--track-scale` existe:** si el círculo mide 100 px, el tracker juntaría celdas de FOMO solo a menos de 25 px (0.25 radios), y una abeja grande se vería como dos. Con `--track-scale 220`, el círculo decide **dónde** se cuenta y la escala decide **cómo** se sigue a la abeja.

### 3.4 Detección

| Opción | Defecto | Recomendado | Qué hace |
| :--- | :--- | :--- | :--- |
| `--threshold` | 0.55 | 0.7 | Confianza mínima para que una detección cree una abeja **nueva**. Más alto: menos abejas falsas, pero puede perder abejas borrosas. |
| `--assoc-threshold` | 0.35 | 0.35 | Confianza mínima para **seguir** a una abeja que ya existe. Es más bajo porque una abeja en movimiento sale borrosa y el modelo duda más. |

**Doble umbral:** una detección débil puede continuar a una abeja conocida, pero solo una fuerte crea una nueva. Además, una abeja nueva necesita 2 detecciones seguidas para tener un ID; una mancha que aparece una sola vez no se convierte en abeja.

### 3.5 Seguimiento (tracker)

| Opción | Defecto | Recomendado | Qué hace |
| :--- | :--- | :--- | :--- |
| `--tracker` | v2 | v2 | `v2`: Kalman + Húngaro, en radios y segundos. `v1`: el primer tracker, en píxeles y frames. Se deja solo para comparar. |
| `--max-gate` | 1.2 | 0.9 | Distancia máxima, en escalas, entre donde el Kalman predijo a la abeja y la detección que se le asigna. Más chico: las abejas no "saltan" a una vecina. Más grande: se siguen mejor los movimientos rápidos. |
| `--max-gate-tentative` | = `--max-gate` | 1.2 | Lo mismo, pero para abejas recién aparecidas que aún no tienen ID confirmado. Más grande, para enlazar una abeja que entra volando rápido. |
| `--accel-std` | 40 | 260 | Cuánto puede acelerar una abeja según el Kalman (escalas/s²). Un valor alto le dice al filtro que la abeja puede cambiar de velocidad de golpe, como al despegar. |
| `--max-lost` | 0.6 | 0.3 | Segundos que una abeja puede pasar sin ser detectada antes de darla por perdida. Más corto: menos "fantasmas" que roban detecciones a otras abejas. |
| `--max-disappeared`, `--max-distance` | 20, 250 | – | Solo para `--tracker v1` (en frames y píxeles). |

**El filtro de Kalman en una frase:** guarda la posición y la velocidad de cada abeja, predice dónde estará en la siguiente imagen y corrige esa predicción con la detección real. Si la abeja no se ve por un momento, la sigue moviendo según su velocidad, y su incertidumbre crece.

**El algoritmo Húngaro en una frase:** cuando hay varias abejas y varias detecciones, prueba todas las combinaciones de forma eficiente y elige la que da la menor distancia total. Así dos abejas que se cruzan no intercambian su identidad.

### 3.6 Conteo

| Opción | Defecto | Recomendado | Qué hace |
| :--- | :--- | :--- | :--- |
| `--counter` | v2 | **hibrido** | `v2`: un evento por abeja, según dónde nació y dónde terminó su recorrido. `hibrido`: cuenta cada salida que cruza el borde, aunque la abeja ya tuviera un recorrido largo, y las entradas como `v2`. |
| `--cancel-s` | 0.5 | 1.0 | Si una abeja sale y vuelve a entrar en menos de estos segundos, no cuenta ninguno de los dos cruces: solo se asomó. |
| `--proj-min-speed` | 1.5 | 3.0 | Cuando se pierde una abeja cerca del borde, se proyecta hacia dónde iba. Solo se proyecta si iba a más de esta velocidad (escalas/s). Más alto: menos salidas inventadas. Con `--flash-exits` esta proyección se apaga. |

**Por qué existe `hibrido`:** en la piquera hay recorridos que duran 10 o 20 segundos, porque el tracker se queda pegado a una guardiana y salta a la abeja que despega. Con `v2`, ese recorrido ya había contado algo y la salida se perdía.

### 3.7 Salidas difíciles: despegues borrosos

El punto débil del sistema son las salidas. Una abeja que despega aparece borrosa en solo 1 o 2 imágenes, y el tracker pide 2 detecciones seguidas para crear una abeja.

| Opción | Defecto | Recomendado | Qué hace |
| :--- | :--- | :--- | :--- |
| `--flash-exits` | apagado | **encendido** | Cuenta como salida una "aparición fugaz": 1 a 3 detecciones fuera del círculo que se alejan de la piquera y que no pertenecen a una abeja ya seguida. Recupera despegues que el tracker no alcanza a seguir. |
| `--static-s` | ninguno | 2 | Descarta una salida si en ese mismo punto ya había una detección en los 2 segundos anteriores. Una abeja que se va no sale de donde ya había algo quieto (una sombra, por ejemplo). |
| `--rep-s` | ninguno | 60 | Recuerda, durante 60 s, los puntos fijos donde el modelo "ve" algo a ratos. Una salida fugaz en un punto que ya se encendió varias veces no cuenta: es fondo, no una abeja. Se aprende del propio video, sin fotos del fondo. |
| `--rep-k` | 2 | 2 | Cuántas veces tiene que encenderse un punto para considerarlo fondo. |

En el `0040-1`, `--flash-exits` subió el F1 de salidas de 0.47 a 0.69, y con `--core 0.5 --cancel-s 1.0` a 0.72.

### 3.8 Colmenas nuevas: manchas del fondo

En una colmena que el modelo no conoce, algunas manchas del fondo se detectan como abeja casi todo el tiempo. El tracker las sigue como abejas quietas y, cuando una abeja real pasa cerca, salta a ella y cuenta una entrada falsa.

| Opción | Defecto | Para colmena nueva | Qué hace |
| :--- | :--- | :--- | :--- |
| `--in-max-age` | ninguno | 3 | Una entrada solo cuenta si esa abeja apareció hace 3 s o menos. La abeja que llega entra enseguida (la más lenta del `0040-1` tardó 1.7 s); un recorrido viejo que "entra" es una guardiana o una mancha. |
| `--in-park-s` | ninguno | 0.15 | Una entrada no cuenta si justo antes la "abeja" estuvo quieta fuera del círculo 0.15 s o más: era una mancha que saltó a una abeja. |
| `--park-s` | ninguno | 0.9 | Un recorrido quieto 0.9 s o más fuera del círculo se marca como estacionado, para que no tape los despegues que pasan cerca. En la prueba a ciegas no ayudó: agregó 4 salidas falsas. Se mantiene porque es parte de la configuración congelada de esa prueba. |

### 3.9 Reglas que dependen de otras

- `--static-s`, `--rep-s` y `--park-s` necesitan `--flash-exits`. Si falta, `main.py` se detiene y lo dice.
- `--flash-exits`, `--in-max-age` y `--in-park-s` necesitan `--counter hibrido`. Si falta, `main.py` se detiene y lo dice.
- `--core`, `--cancel-s` y `--proj-min-speed` solo tienen efecto con `--counter hibrido`. Sin él no dan error, pero no hacen nada.

## 4. Cómo ubicar la piquera en un video nuevo

1. Correr unos segundos con `--no-output --snapshot-every 30` y el círculo en una posición aproximada.
2. Abrir la primera imagen de `snapshots/` y ver dónde quedó el círculo amarillo.
3. Ajustar `--roi-x`, `--roi-y` y `--roi-r` hasta que el círculo rodee la boca del tubo y la zona donde las abejas aterrizan. Si el círculo se sale de la imagen, `main.py` avisa por qué lado y qué valores son válidos.
4. Si hay guardianas que vuelan frente al tubo, achicar el círculo y agregar `--track-scale` con el tamaño anterior (ver 3.3).

**Regla para una prueba honesta:** en un video de prueba solo se elige el círculo, mirando la primera imagen y antes de contar. Nada más se ajusta después de ver el resultado.

| Video | `--roi-x` | `--roi-y` | `--roi-r` | Extra |
| :--- | :---: | :---: | :---: | :--- |
| `0040-1` (colmena 004) | 900 | 600 | 220 | – |
| `0031-2` (colmena 003) | 855 | 465 | 100 | `--track-scale 220` |
| `0020-1` (colmena 002) | 570 | 815 | 180 | – |
| Colmena 001 | ver `data/rois_001.csv` | | | la cámara se movió entre videos |

## 5. Qué muestra la pantalla

- **Círculo amarillo:** borde de conteo.
- **Círculo magenta:** boca de la piquera (`--core`).
- **Rectángulo naranja:** la parte de la imagen que ve el modelo (`--crop-roi`).
- **Punto rojo con "ID n":** una abeja seguida por el tracker.
- **Puntos azules que se desvanecen:** el recorrido reciente de cada abeja.
- **Tablero arriba a la izquierda:** entradas (verde) y salidas (rojo) acumuladas.

Al terminar, la consola muestra el resumen: entradas, salidas, velocidad y si el análisis fue al ritmo del video.

## 6. Preguntas frecuentes

**¿Por qué FOMO y no YOLO?**
FOMO pesa 54 KB y en la Pi 5 analiza unas 90 imágenes por segundo. Se probó un YOLO en Edge Impulse (v9): daba mAP@50 de 0.62 en test y tardaba 188 ms por imagen en una Pi 4, unas 10 veces más lento. Para contar solo hace falta el centro de cada abeja, no su caja.

**¿Por qué se mide con F1 evento por evento y no con totales?**
Un total puede coincidir por casualidad: 30 entradas contadas pueden ser 15 reales y 15 falsas. Comparar evento por evento (tiempo ±0.5 s y lado de la piquera) obliga a que cada conteo corresponda a una abeja real. El F1 combina precisión (cuántos de los contados son reales) y recall (cuántos de los reales se contaron).

**¿Qué es el "F1 al azar"?**
Es el F1 que se obtiene moviendo en el tiempo los mismos eventos del programa. Si el resultado real no lo supera claramente, el programa no está contando mejor que el azar. En estos videos va de 0.01 a 0.40.

**¿Qué es la prueba a ciegas?**
Se entrenó un modelo (v7) sin ninguna imagen de la colmena 005, se congelaron las reglas con un commit y se corrió una sola vez en dos videos de esa colmena, contados a mano sin mirar el resultado. Dio F1 0.78 en entradas y 0.66 en salidas. Es una sola colmena y 64 eventos, así que es una primera evidencia, no una prueba definitiva.

**¿Por qué las salidas salen peor que las entradas?**
La abeja que entra camina o aterriza despacio y se ve en muchas imágenes. La que sale despega muy rápido y aparece borrosa en una o dos. El límite está en el detector, no en el tracker: incluso el modelo que conoce la colmena llega a ~0.77 en salidas.

**¿Por qué tantos parámetros?**
Cada regla resuelve un error concreto que se vio en un video: guardianas (`--core`), abejas que se asoman (`--cancel-s`), despegues borrosos (`--flash-exits`), sombras (`--static-s`) y manchas del fondo (`--rep-s`, `--in-max-age`, `--in-park-s`). Para un uso normal basta con copiar la configuración recomendada y ajustar solo el círculo.
