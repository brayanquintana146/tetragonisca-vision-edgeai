# Pendientes — tetragonisca-vision-edgeai

Última actualización: 7 de octubre de 2026. Rama con lo de hoy: `feature/puntos-fijos-repetidos` (sale de `feature/algoritmo-conteo`, sin subir a GitHub).

Lo hecho está en el [README](../README.md), en [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md) y en [PRUEBA_CIEGA_V7.md](PRUEBA_CIEGA_V7.md) (protocolo y tablas completas de la prueba sin trampa).

## Estado actual

- **Meta:** que el modelo cuente bien en una colmena que nunca vio, sin cargar fotos de su fondo.
- **Modelos:**
  - v7 `fomo_sin005_480_int8.lite`: nunca vio la 005. Es el de la meta.
  - v8 `fomo_sin005_confondo_480_int8.lite`: v7 + 50 fotos del fondo de la 005.
  - v5 `fomo_borrosas_480_int8.lite`: vio la 005. Referencia.
  - Ninguno vio la 002. La 006 no se usa (cámara en mano).
- **Configuración del examen:**
  ```powershell
  --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --rep-s 60 --in-max-age 3 --in-park-s 0.15 --park-s 0.9
  ```
  Por video solo se elige la zona de entrada mirando el primer cuadro. En la 005: `--roi-r 100 --track-scale 220`.

**Examen a ciegas en la 005** (`0056-7` y `00519-20`, contados a mano: 31 entradas y 33 salidas; una sola corrida). Cada celda es bien / contadas y F1.

| Modelo | Entradas | Salidas |
| :--- | :---: | :---: |
| v7 (nunca vio la 005) | 21 / 23, 0.78 | 20 / 28, 0.66 |
| v8 | 24 / 25, 0.86 | 17 / 26, 0.58 |
| v5 (vio la 005) | 25 / 28, 0.85 | 23 / 27, 0.77 |

- **Conclusión honesta:** v7 funciona en una colmena nueva sin fotos del fondo, pero por debajo del modelo que la conoce. El punto débil son las salidas y el límite es el detector: ni v5 encuentra más de 7 de cada 10, porque la abeja que despega sale borrosa.
- **Videos con conteo a mano** (`data/gt_*.csv`): `0040-1` (dos conteos, coinciden en 110 de 112), `0031-2`, `00511-12`, `0056-7`, `00519-20`.

## Pendientes (en orden de importancia)

### 1. Entrenar con más abejas borrosas — Brayan

Es lo que más puede mejorar las salidas. Hoy las 273 borrosas del entrenamiento son todas de la colmena 004.

1. Sacar cuadros de videos de la colmena 003 con `scripts/05_extraer_borrosas.py`.
2. Etiquetarlos en Edge Impulse. Separar train y test **por video**.
3. Entrenar igual que v7: 480×480, FOMO, **con la 005 desactivada**. Guardarlo como versión nueva (v9) y exportar el `.lite` a `models/` con otro nombre.
4. Avisar a Claude: el modelo nuevo pasa por el mismo examen con las mismas reglas congeladas.

**Videos que NO se pueden usar para entrenar:**
- Colmena 005 completa (si no, el modelo deja de ser "nunca vio la 005"), 002 y 006.
- Los contados a mano o usados en pruebas: `0040-1`, `00427-28`, `0031-2`.

### 2. Etiquetar despegues reales — Claude prepara, Brayan etiqueta

`--flash-exits` ya encuentra muchos despegues. Claude saca esos cuadros de videos de la 003 y la 004 (mismas exclusiones del punto 1) para que Brayan solo revise y etiquete. Van al mismo modelo v9.

- Falta: que Brayan confirme para empezar.

### 3. Contar a mano más videos — Brayan

No mejora el resultado, pero lo hace más firme: el examen de hoy son 2 minutos y 64 eventos.

- Videos de la 005 sin tocar: `0053-4`, `0054-5`, `0057-8`, `0059-10`, `00510-11`, `00513-14`, `00515-16`, `00520-21`, `00522-23`, `00524-25`. Pedir a Claude la zona de entrada antes de anotar; Claude no los corre hasta congelar la versión que se quiera examinar.
- `00523-24`: ya se corrió en el examen; contarlo suma eventos al examen de hoy (`--roi-x 1075 --roi-y 640 --roi-r 100`).
- `0020-1` (colmena 002): sigue sin conteo a mano (`--roi-x 570 --roi-y 815 --roi-r 180`).
- Reglas al anotar: no contar guardianas, y marcar cuando la abeja cruza el círculo.

### 4. Decidir sobre `--park-s` — Claude

El análisis por partes del examen sugiere que no ayuda (agregó 4 salidas falsas a v7). Quitarla es una decisión de desarrollo: la versión sin `--park-s` necesita otro examen a ciegas, con videos del punto 3, antes de poder citarla.

### 5. Orden de lo de hoy — Claude, cuando Brayan diga

- Unir `feature/puntos-fijos-repetidos` a `feature/algoritmo-conteo` y subirla a GitHub.
- Pasar a `bench/` los scripts de la prueba (detección foto por foto, detecciones de varios modelos, conteo por grupos, manchas inyectadas). Hoy están en `prueba_v7_colmena005.zip` y `segunda_ronda_v7.zip`, en la biblioteca del proyecto.
- Edge Impulse: confirmar que las muestras de la 005 quedaron como se quiere (activadas para la línea v5, desactivadas para la línea v7).

### 6. Cámara con exposición más corta — en espera

Si el despegue sale menos borroso, el detector lo ve más cuadros. Solo aplica a la cámara de Cusco. Brayan no puede hacerlo por ahora.

- **C930e en la Pi:** probar exposiciones cortas con `v4l2-ctl` (`deployment.md`, sección 5).
- **FPS:** la C930e graba a 30 fps y las reglas se ajustaron a 60 fps. Revisar `max_hits` y `max_gap_s` de `FlashExits` con un video de esa cámara.
- **Cámara fija:** el sistema supone que la piquera no se mueve en la imagen.

### 7. Eventos con hora real — después

Que `--events` guarde la hora real de cada evento, escriba a disco de inmediato y corte un archivo por día. Lo necesita el proyecto de análisis (`analisis_presentacion_results`).

## Cómo probar sin hacer trampa

1. Las reglas del contador se ajustan solo con el `0040-1` y videos de las colmenas 001/003/004. Nunca con videos de la 005 ni de la 002.
2. Por video solo se elige la zona de entrada, mirando el primer cuadro, antes de contar.
3. Se congela la versión (commit) y se corre **una sola vez**. Ese es el resultado, aunque salga mal.
4. El conteo a mano se hace sin ver lo que contó el programa, y se abre después de correr.
5. Si después se cambia algo mirando ese video, el resultado nuevo ya es de desarrollo.
6. No elegir la mejor fila después de ver el examen. El resultado oficial es el de la versión congelada.
7. Los errores de `0056-7`, `00519-20` y `00523-24` no se revisan uno por uno: así sirven otra vez para examinar un modelo reentrenado.

## Otros pendientes

- **Rotar las API keys de Edge Impulse:** se compartieron dos (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys*.
- **Cambiar las contraseñas de la Pi y del hotspot:** se quitaron de `deployment.md`, pero siguen en el historial de git.
- **Orden del repositorio:**
  - licencia inconsistente (MIT en el badge, BSD 3-Clause en el repo);
  - revisar `output_result.mp4` y `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`;
  - `bench/make_scenarios.py` necesita TensorFlow como respaldo en Windows;
  - `test_tracker.py` (EuTrack v1) falla desde antes de estos cambios.
