# Pendientes — tetragonisca-vision-edgeai

Última actualización: 7 de octubre de 2026 (tarde). Rama con lo de hoy: `feature/puntos-fijos-repetidos` (sale de `feature/algoritmo-conteo`, sin subir a GitHub).

Lo hecho está en el [README](../README.md), en [TRACKING_ALGORITHM.md](TRACKING_ALGORITHM.md) y en [PRUEBA_CIEGA_V7.md](PRUEBA_CIEGA_V7.md) (protocolo y tablas completas de la prueba sin trampa).

## Para arrancar la próxima sesión

Leer esta lista y [PRUEBA_CIEGA_V7.md](PRUEBA_CIEGA_V7.md). Lo primero es resolver "Por confirmar con Brayan" y después seguir el orden de "Pendientes".

### Por confirmar con Brayan

1. **Cambio de nombre de los modelos.** Está hecho en `feature/algoritmo-conteo` pero **sin commit**: archivos de `models/` con la versión al inicio y referencias en `main.py`, `README.md`, `deployment.md`, `docs/PENDIENTES.md`, `bench/` y `scripts/`. Falta su sí para el commit. En esta rama (`feature/puntos-fijos-repetidos`) la documentación todavía usa los nombres viejos en algunos sitios.
2. **Unir esta rama a `feature/algoritmo-conteo`** y subirla a GitHub. Falta su sí.
3. **Sacar los cuadros borrosos** de la 001 y la 003 y los despegues de la 003 y la 004. Falta su sí (implica descomprimir `001 - MOT.zip`, 1.8 GB).
4. **Raspberry Pi:** si tiene modelos con el nombre viejo, renombrarlos o copiarlos de nuevo.

## Estado actual

- **Meta:** que el modelo cuente bien en una colmena que nunca vio, sin cargar fotos de su fondo.
- **Modelos** (nombre nuevo, con la versión al inicio; coincide con las versiones de Edge Impulse):

  | Versión | Archivo | Qué es |
  | :--- | :--- | :--- |
  | v3 | `v3_fomo_tetragonisca_int8.lite` | colmenas 004, 005, 001 y 003. 320×320 |
  | v4 | `v4_fomo_nuevo_int8.lite` | v3 + 196 despegues del `0040-1`. 320×320. Rama aparte |
  | v5 | `v5_fomo_borrosas_480_int8.lite` | v3 sin el `0040-1` + 273 borrosas de la 004. 480×480. Referencia |
  | v6 | `v6_fomo_borrosas_320_int8.lite` | v5 en 320×320 |
  | v7 | `v7_fomo_sin005_480_int8.lite` | v5 sin la colmena 005. **El de la meta** |
  | v8 | `v8_fomo_sin005_confondo_480_int8.lite` | v7 + 50 fotos del fondo de la 005 |
  | v9 | (sin archivo) | v5 con YOLO-Pro. Descartado por lento |
  | v10 | (por entrenar) | v7 + borrosas de la 001 y la 003 |

  Ninguno vio la 002. La 006 no se usa (cámara en mano).
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
- **Límites de la evidencia:** una sola colmena nueva, 2 minutos y 64 eventos, un solo anotador, colmenas del mismo conjunto de datos.

## Decisión del 7 oct: la referencia es el conteo a mano, no el *Pseudo*

Desde hoy los resultados se miden contra el conteo a mano de Brayan, evento por evento. El *Pseudo* del paper queda solo como dato secundario.

Por qué:
- El *Pseudo* lo hizo una persona ayudada por el tracker del propio paper (EuTrack), así que no es independiente.
- Solo da totales. Un total puede coincidir por casualidad aunque los eventos estén mal.
- Incluye guardianas; el conteo a mano no (definición de este proyecto).
- No es exacto: en la colmena 001 el biólogo y el *Pseudo* difieren hasta en 16 entradas en un video.

**Reglas del conteo a mano:** no contar guardianas, ni cuando entran ni cuando salen; marcar cuando la abeja cruza el círculo; clic sobre la abeja; no mirar lo que contó el programa.

**Cómo probó el paper** (Leocádio et al., BRACIS 2023), para citarlo bien:
- Detector: 2100 fotos de las 6 colmenas, repartidas en 1500 / 300 / 300. Las tres partes tienen las mismas colmenas: no mide una colmena nueva.
- Conteo: un video por colmena más 6 videos de la 001, comparando totales contra el *Pseudo* con error relativo promedio.
- Usa YOLOv8x, un modelo grande que no corre en una Raspberry.

**Videos con conteo a mano** (`data/gt_*.csv`):

| Video | Colmena | Uso | Entradas / salidas |
| :--- | :--- | :--- | :---: |
| `0040-1` | 004 | desarrollo (dos conteos, coinciden en 110 de 112) | 36 / 78 |
| `0031-2` | 003 | desarrollo | 37 / 18 |
| `00511-12` | 005 | a ciegas para `--rep-s`; desarrollo para lo demás | 23 / 13 |
| `0056-7` | 005 | examen | 3 / 9 |
| `00519-20` | 005 | examen | 28 / 24 |

## Colmena 001: lo que hay que saber antes de usarla

- **Sí tiene videos:** 36, dentro de `all_datasets\001 - MOT.zip` (sin descomprimir). 15 traen archivo de conteo *Pseudo*.
- **Sus fotos se recortaron antes de subirlas a Edge Impulse** (solo esta colmena): de 1920×1080 a 1280×720 desde (260, 100), con FastStone. Las abejas quedaron 1.5 veces más grandes. Ver README, paso 2.5, y `scripts/fix_crop_labels.py`.
- **Consecuencia:** el modelo conoce las abejas de la 001 agrandadas. Para sacar borrosas o para contar en un video de la 001 hay que usar el mismo aumento: un cuadrado de 720 px alrededor de la piquera, no de 1080. `scripts/05_extraer_borrosas.py` y `main.py --crop-roi` hoy usan 1080: falta agregar una opción de tamaño de recorte.
- **La cámara se movió una vez:** la piquera aparece en dos posiciones según el video. Dos fotos de muestra que mandó Brayan (ya recortadas a 1280×720):
  - `0012-3` (cuadro 316): boca del tubo cerca de (510, 185) en la foto recortada, o sea (770, 285) en el video original.
  - `0018-9` (cuadro 3075): boca cerca de (410, 360) en la foto recortada, o sea (670, 460) en el video original.
  - Son valores leídos a ojo de una foto: sirven de guía. Falta ver entre qué videos ocurrió el cambio y fijar la zona de entrada de cada video mirando su primer cuadro.
- La 001 es una colmena conocida por todos los modelos: sirve para entrenar y para desarrollo, no para pruebas a ciegas.

## Pendientes (en orden de importancia)

### 1. Entrenar el modelo v10 con más abejas borrosas — Claude prepara, Brayan etiqueta y entrena

Es lo que más puede mejorar las salidas. Hoy las 273 borrosas son todas de la colmena 004.

| Colmena | Borrosas hoy | Videos para sacar | Estimado |
| :--- | :---: | :---: | :---: |
| 001 | 0 | 21 (los 36 menos los 15 con *Pseudo*, que se apartan) | 100 a 150 |
| 003 | 0 | 40 (sin el `0031-2`) | 200 a 280 |
| 004 | 273 | ya usada | – |

El estimado sale de las ~6 por video de la 004; el número real depende de la actividad.

Pasos:
1. (Claude) Agregar a `scripts/05_extraer_borrosas.py` la opción de tamaño de recorte, para la 001.
2. (Claude) Descomprimir `001 - MOT.zip`, fijar la zona de entrada por grupo de videos y sacar los cuadros de la 001 y la 003.
3. (Brayan) Revisar y etiquetar en Edge Impulse. Apartar 5 o 6 videos completos de cada colmena para test: nunca cuadros del mismo video en train y en test.
4. (Brayan) Entrenar igual que v7: 480×480, FOMO, **con la 005 desactivada**. Guardarlo como v10 y exportar `models/v10_..._int8.lite`.
5. (Claude) Pasar v10 por el mismo examen, con las mismas reglas congeladas.

**Videos que NO se pueden usar para entrenar:**
- Colmena 005 completa (si no, el modelo deja de ser "nunca vio la 005"), 002 y 006.
- Los contados a mano o usados en pruebas: `0040-1`, `00427-28`, `0031-2`.
- Los 15 videos de la 001 con *Pseudo*, que se apartan para desarrollo.

### 2. Etiquetar despegues reales — Claude prepara, Brayan etiqueta

`--flash-exits` ya encuentra muchos despegues. Claude saca esos cuadros de videos de la 001, la 003 y la 004 (mismas exclusiones del punto 1) para que Brayan solo revise y etiquete. Van al mismo modelo v10.

### 3. Contar a mano más videos — Brayan

Brayan decidió contar todo lo que haga falta, sin importar el tiempo. Orden sugerido:

1. **Examen de la 005, más eventos:** `00523-24` (ya se corrió; `--roi-x 1075 --roi-y 640 --roi-r 100`).
2. **Colmena 002, la que ningún modelo vio:** `0020-1` (`--roi-x 570 --roi-y 815 --roi-r 180`). Es desarrollo, pero da la primera medida evento por evento en la 002.
3. **Más videos de la 005 sin tocar**, para un segundo examen: `0053-4`, `0054-5`, `0057-8`, `0059-10`, `00510-11`, `00513-14`, `00515-16`, `00520-21`, `00522-23`, `00524-25`. Pedir a Claude la zona de entrada antes de anotar. Claude no los corre hasta congelar la versión que se quiera examinar.
4. **Videos de la 002 sin tocar** (25 más), para una segunda colmena nueva. Es lo que más fortalece la afirmación de que generaliza.
5. **Desarrollo:** `00521-22` y `0055-6` (005), `00517-18` (005) y algunos de la 001, para ajustar reglas con más de dos videos.

Comando (desde la carpeta del repo):
```powershell
python tools/anotar_eventos.py --video "RUTA\VIDEO.mp4" --roi-x X --roi-y Y --roi-r R --out data/gt_VIDEO.csv
```

### 4. Repetir la prueba dejando fuera otra colmena — después del v10

Hoy la evidencia es de una sola colmena nueva (la 005). Para decir que generaliza hace falta repetirlo: entrenar sin la 003 y examinar en la 003, y lo mismo con la 004. Y examinar en la 002, que ningún modelo vio.

### 5. Decidir sobre `--park-s` — Claude

El análisis por partes del examen sugiere que no ayuda (agregó 4 salidas falsas a v7). Quitarla es una decisión de desarrollo: la versión sin `--park-s` necesita otro examen a ciegas, con videos del punto 3, antes de poder citarla.

### 6. Orden del repo — Claude, cuando Brayan diga

- Lo de "Por confirmar con Brayan": commit del cambio de nombres, unir la rama, subirla.
- Pasar a `bench/` los scripts de la prueba (detección foto por foto, detecciones de varios modelos, conteo por grupos, manchas inyectadas). Hoy están en `prueba_v7_colmena005.zip` y `segunda_ronda_v7.zip`, en la biblioteca del proyecto, y usan los nombres viejos de los modelos.
- Quitar del README las comparaciones contra el *Pseudo* como medida principal y dejarlas como dato secundario.
- Edge Impulse: confirmar que las muestras de la 005 quedaron como se quiere (activadas para la línea v5, desactivadas para la línea v7 y v10).

### 7. Cámara con exposición más corta — en espera

Si el despegue sale menos borroso, el detector lo ve más cuadros. Solo aplica a la cámara de Cusco. Brayan no puede hacerlo por ahora.

- **C930e en la Pi:** probar exposiciones cortas con `v4l2-ctl` (`deployment.md`, sección 5).
- **FPS:** la C930e graba a 30 fps y las reglas se ajustaron a 60 fps. Revisar `max_hits` y `max_gap_s` de `FlashExits` con un video de esa cámara.
- **Cámara fija:** el sistema supone que la piquera no se mueve en la imagen.

### 8. Eventos con hora real — después

Que `--events` guarde la hora real de cada evento, escriba a disco de inmediato y corte un archivo por día. Lo necesita el proyecto de análisis (`analisis_presentacion_results`).

## Cómo probar sin hacer trampa

1. Las reglas del contador se ajustan solo con videos de desarrollo de las colmenas 001/003/004 (hoy: `0040-1` y `0031-2`). Nunca con videos de examen.
2. Por video solo se elige la zona de entrada, mirando el primer cuadro, antes de contar.
3. Se congela la versión (commit) y se corre **una sola vez**. Ese es el resultado, aunque salga mal.
4. El conteo a mano se hace sin ver lo que contó el programa, y se abre después de correr.
5. Si después se cambia algo mirando ese video, el resultado nuevo ya es de desarrollo.
6. No elegir la mejor fila después de ver el examen. El resultado oficial es el de la versión congelada.
7. Los errores de `0056-7`, `00519-20` y `00523-24` no se revisan uno por uno: así sirven otra vez para examinar un modelo reentrenado.
8. Siempre comparar contra la columna "F1 azar" de `bench/compare_events.py --tol 0.5 --max-angle 40`.

## Otros pendientes

- **Rotar las API keys de Edge Impulse:** se compartieron dos (ingestión y Admin) en un chat. Revocarlas en *Dashboard → Keys*.
- **Cambiar las contraseñas de la Pi y del hotspot:** se quitaron de `deployment.md`, pero siguen en el historial de git.
- **Orden del repositorio:**
  - licencia inconsistente (MIT en el badge, BSD 3-Clause en el repo);
  - revisar `output_result.mp4` y `CARPETA_COFRE_MOVER_CARPETA_PRINCIPAL`;
  - `bench/make_scenarios.py` necesita TensorFlow como respaldo en Windows;
  - `test_tracker.py` (EuTrack v1) falla desde antes de estos cambios.
