# Pendientes — tetragonisca-vision-edgeai

Última actualización: 5 de octubre de 2026 (noche). Rama: `feature/algoritmo-conteo`.

Lo hecho está en el [README](../README.md) (configuración recomendada, validación del conteo y prueba de generalización) y en [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md) (contador híbrido, salidas fugaces, boca de la piquera, puntos quietos y escala del tracker). Los números para las láminas están en `/mnt/project-files/tetragonisca/resultados_presentacion.md`.

## Estado actual

- **Modelo:** v5, 480×480, con 273 abejas borrosas (`models/fomo_borrosas_480_int8.lite`). *Model testing*: F1 0.94.
- **Configuración recomendada:**
  ```powershell
  --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0
  ```
  Por colmena se fijan ROI, `--core` y `--track-scale` mirando la imagen.
- **Colmenas en el entrenamiento** (historial de Edge Impulse): 001, 003, 004 y 005. **Nunca vistas:** 002 y 006.

| Video | Colmena | Tipo | Salidas | Entradas | Referencia (sal. / ent.) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `0040-1` | 004 (conocida) | desarrollo, anotado a mano | 47 (F1 0.72) | 33 (F1 0.84) | 78 / 36 (a mano) |
| `0031-2` | 003 (conocida) | desarrollo | 25 | 40 | 21 / 32 |
| `00517-18` | 005 (conocida) | primera corrida ciega: 20 / 23; calibrada: 23 / 32 | 18 | 30 | 16 / 30 |
| `0020-1` | 002 (**nueva**) | **ciega: 43 / 8**; luego se creó `--static-s` | 16 | 8 | 7 / 11 |
| `0062-2M` | 006 (**nueva**) | ciega, cámara en mano: no sirve para medir | 25 | 42 | 15 / 17 |

Las salidas y entradas de la tabla son con `--static-s 2`. En el `0031-2` y el `00517-18` salen del replay de las detecciones guardadas, todavía no corridas en el PC.

- **Conclusión honesta:** en colmenas conocidas el conteo queda cerca de la referencia. En la única colmena nueva válida (`0020-1`) la corrida ciega falló en las salidas por una sombra. Todavía no se puede decir que generaliza.

## Pendientes (en orden)

### 1. Dejar fuera la colmena 005 (*leave-one-hive-out*) — decidido el 5 oct

Objetivo: tener una segunda colmena nueva para el modelo, con referencia *Pseudo*.

1. **Edge Impulse:** la v5 ya está guardada como versión. En *Data acquisition*, filtrar las imágenes de la colmena 005 y desactivarlas (*Disable*), tanto en entrenamiento como en test.
2. **Entrenar** con los mismos ajustes que la v5 (480×480, FOMO). Anotar el F1 de *Model testing* (ahora sin imágenes de la 005).
3. **Exportar** el modelo int8 como `models/fomo_sin005_480_int8.lite`. No subirlo a git.
4. **Correr el `00517-18` una sola vez**, con la configuración recomendada y la ROI del paper: `--roi-x 1032 --roi-y 700 --roi-r 180 --track-scale 220 --core 0.7 --static-s 2`. Correr lo mismo con el modelo v5 para comparar en igualdad de condiciones.
5. **Comparar** los dos contra el *Pseudo* (16 salidas / 30 entradas). Lo que importa es cuánto empeora al quitar la colmena del entrenamiento.
6. **Si da tiempo,** repetir con la colmena 003 y el `0031-2`.

Ojo: la ROI y el core del `00517-18` se eligieron mirando ese video, así que esto mide la generalización del **detector**, no la de los ajustes del conteo.

### 2. Preparar la presentación

- **Qué decir:**
  - entradas: F1 0.84 en el `0040-1`;
  - salidas: de 0.47 a 0.72, con la causa medida (el despegue se ve 1–2 frames);
  - en colmenas conocidas, más cerca de la referencia que los trackers del paper.
- **Límites que hay que decir:**
  - solo una prueba válida en colmena nueva (`0020-1`), y falló en salidas (43 contra 7);
  - los ajustes se eligieron con los videos de desarrollo;
  - el *Pseudo* solo da totales;
  - los datos son de colmenas de otros investigadores; la colmena final está en Cusco y la cámara aún no se instala.
- **Cómo contar lo del `0020-1`:** falló, se encontró la causa (sombra), se agregó una regla general (`--static-s`) que bajó a 16 sin empeorar los otros videos, y falta confirmarla en otra colmena nueva.
- **Demo:** correr el sistema en la Raspberry Pi con los videos grabados. No usar la cámara filmando un celular: el parpadeo, los reflejos y el tamaño cambian los resultados. Si se quiere mostrar la C930e, unos segundos en vivo solo para ver que captura.

### 3. Medir los FPS del modelo 480 en la Raspberry Pi 5

El resumen final de `main.py` ya dice los FPS y si alcanza el tiempo real.

### 4. Extraer los despegues reales para reentrenar (opcional)

`--flash-exits` encuentra los despegues, así que se puede usar para sacar esos frames de los 44 videos de la 004 y etiquetarlos. Nunca del `0040-1`.

### 5. Cámara (en espera)

- **C930e en la Pi:** probar exposiciones cortas con `v4l2-ctl` (`deployment.md`, sección 5).
- **FPS:** la C930e graba a 30 fps; `FlashExits` se ajustó a 60 fps. Revisar `max_hits` y `max_gap_s` con un video de esa cámara.
- **Cámara fija:** el sistema supone que la piquera no se mueve en la imagen (por eso falló el `0062-2M`).

## Cómo probar un video nuevo (sin hacer trampa)

1. Confirmar que la colmena no está en el entrenamiento.
2. Sacar frames (inicio, mitad y final) y fijar ROI, `--core` y `--track-scale` **solo mirando la imagen**. Si la resolución es menor, escalar ROI y `--track-scale` en la misma proporción.
3. Revisar la posición con `--snapshot-every 150 --snapshot-dir snapshots_X`, sin mirar los conteos.
4. Correr **una sola vez** con `--output` y `--events` y comparar contra el `.txt` del video. Ese es el resultado, aunque salga mal.
5. Si después se cambia algo mirando ese video, el resultado nuevo ya es de desarrollo.

Para analizar un video sin volver a correr el modelo: `bench/dump_detections.py` (con el mismo `--roi-x/--roi-y` y `--crop-roi`) y `bench/replay_detections.py`.

## Otros pendientes

- **Rotar las API keys de Edge Impulse:** se compartieron dos (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys*.
- **Cambiar las contraseñas de la Pi y del hotspot:** se quitaron de `deployment.md`, pero siguen en el historial de git.
- **Orden del repositorio:**
  - licencia inconsistente (MIT en el badge, BSD 3-Clause en el repo);
  - revisar `output_result.mp4` y `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`;
  - `bench/make_scenarios.py` necesita TensorFlow como respaldo en Windows;
  - `test_tracker.py` (EuTrack v1) falla desde antes de estos cambios.
