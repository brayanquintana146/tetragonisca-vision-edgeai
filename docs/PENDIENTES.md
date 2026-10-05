# Pendientes — tetragonisca-vision-edgeai

Última actualización: 5 de octubre de 2026. Rama: `feature/algoritmo-conteo`.

Lo hecho hasta ahora está en el [README](../README.md) (historial del modelo, configuración recomendada y validación del conteo) y en [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md) (contador híbrido, salidas fugaces, boca de la piquera y escala del tracker).

## Estado actual

- **Modelo:** v5, 480×480, con 273 abejas borrosas (`models/fomo_borrosas_480_int8.lite`). *Model testing*: F1 0.94.
- **Configuración recomendada:**
  ```powershell
  --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --core 0.5 --cancel-s 1.0
  ```
- **`0040-1`** (anotado a mano: 36 entradas, 78 salidas; medición estricta):
  - entradas: 29 bien de 33 contadas, F1 0.84 (azar 0.29);
  - salidas: 46 bien de 49 contadas, F1 0.72 (azar 0.40).
- **`0031-2`** (colmena 003, solo totales *Pseudo* del paper: 32 entradas, 21 salidas): cuenta 40 entradas y 31 salidas, con `--roi-x 855 --roi-y 465 --roi-r 100 --track-scale 220`.
- **Ajustes:** se eligieron con estos dos videos, así que todavía no están confirmados.

## Pendientes (en orden)

### 1. Preparar la presentación

- **Qué funciona:**
  - entradas: F1 0.84, muy sobre el azar;
  - salidas: F1 0.72, antes 0.47. La causa de las pérdidas está medida: la abeja que despega se ve solo 1–2 frames.
- **Comparación con el paper:** en el `0031-2`, sus trackers contaron 73–100 salidas, donde la referencia es 21; este proyecto cuenta 31. En el `0040-1`, sus trackers contaron 21–29 salidas, donde la referencia es 85; este proyecto cuenta 49, con 46 correctas de 78 reales.
- **Método:**
  - medición estricta contra el azar;
  - test separado por video;
  - video de prueba anotado a mano;
  - segundo video de otra colmena.
- **Límites que hay que decir:**
  - los ajustes se eligieron con los mismos dos videos;
  - el `0040-1` es de una colmena que el modelo ya conoce;
  - el *Pseudo* solo da totales.
- **Resumen con los números:** `/mnt/project-files/tetragonisca/resultados_presentacion.md`.

### 2. Confirmar los ajustes con más videos

- **Hecho:** `00517-18` (colmena 005), sin tocar ajustes. Contó 20 salidas y 23 entradas; el *Pseudo* da 16 y 30. Detalle en el README.
- **Siguiente:** otro video sin anotar con *Pseudo*, `0010-1` o `0020-1`, o anotar uno a mano para medir F1.

### 2b. (detalle) Cómo probar un video nuevo

- **Qué video:** uno que no se haya usado para ajustar. Si tiene *Pseudo* en el paper, mejor: `0010-1`, `0020-1`, `00517-18` o `0062-2M`.
- **Ubicar la piquera:** con `--no-output --snapshot-every 30`, y usar `--track-scale 220` si el círculo es chico.
- **Comparar:** los totales contra el `.txt` del video, sin cambiar ningún ajuste.
- **Para medir aciertos (F1)** hay que anotarlo con `tools/anotar_eventos.py`.

### 3. Extraer los despegues reales para reentrenar (opcional)

Las 273 borrosas eran sobre todo abejas volando, no el momento del despegue: las salidas que el detector ve solo subieron de 54% a 58%. `--flash-exits` encuentra justo esos despegues, así que se puede usar para sacar esos frames de los 44 videos de la 004 y etiquetarlos. Nunca del `0040-1`.

### 4. Cámara (en espera)

- **C930e en la Pi:** probar exposiciones cortas con `v4l2-ctl` (`deployment.md`, sección 5), por ejemplo `exposure_time_absolute=30`, que son 3 ms.
- **FPS:** la C930e graba a 30 fps y el `0040-1` es de 60. Habrá que revisar `max_hits` y `max_gap_s` de `FlashExits` con un video de esa cámara.

## Otros pendientes

- **Rotar las API keys de Edge Impulse:** se compartieron dos (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys*.
- **Cambiar las contraseñas de la Pi y del hotspot:** se quitaron de `deployment.md`, pero siguen en el historial de git.
- **Medir los FPS del modelo 480 en la Raspberry Pi 5.**
- **Orden del repositorio:**
  - licencia inconsistente (MIT en el badge, BSD 3-Clause en el repo);
  - revisar `output_result.mp4` y `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`;
  - `bench/make_scenarios.py` necesita TensorFlow como respaldo en Windows;
  - `test_tracker.py` (EuTrack v1) falla desde antes de estos cambios.
