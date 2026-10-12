# Validación del conteo

Este documento explica cómo se midió el conteo de entradas y salidas, qué resultados dio y hasta dónde llegan esos resultados.

## Qué se cuenta

Solo las abejas que **realmente entran** a la colmena o **se van** de ella. No cuentan las guardianas que revolotean frente a la piquera ni las abejas que se asoman y vuelven.

## Cómo se mide

1. **Conteo a mano.** Cada video se anota con `tools/anotar_eventos.py`: se marca el momento y el lugar en que cada abeja cruza el círculo de la piquera. El conteo a mano se hace sin ver lo que contó el programa.
2. **Comparación evento por evento.** `bench/compare_events.py --tol 0.5 --max-angle 40` empareja cada evento del programa con uno anotado del mismo tipo, a menos de 0.5 s y del mismo lado de la piquera (±40°).
3. **Comparación contra el azar.** La columna *F1 azar* es el F1 que se obtiene desplazando en el tiempo los mismos eventos del programa. Un resultado solo vale si lo supera con claridad.

```powershell
python tools/anotar_eventos.py --video VIDEO.mp4 --roi-x X --roi-y Y --roi-r R --out data/gt_VIDEO.csv
python main.py --video VIDEO.mp4 ... --no-output --events eventos.csv
python bench/compare_events.py data/gt_VIDEO.csv eventos.csv --tol 0.5 --max-angle 40 --roi-x X --roi-y Y
```

Se mide contra el conteo a mano y no contra el conteo *Pseudo* publicado con el conjunto de datos, por tres razones: el *Pseudo* solo da totales (un total puede coincidir por casualidad), incluye a las guardianas y se hizo con ayuda del tracker del propio artículo.

Dos conteos a mano del mismo video (`0040-1`), hechos en días distintos, coinciden en 110 de 112 eventos.

### Videos contados a mano

| Video | Colmena | Uso | Entradas / salidas |
| :--- | :--- | :--- | :---: |
| `0040-1` | 004 | desarrollo | 36 / 78 |
| `0031-2` | 003 | desarrollo | 37 / 18 |
| `00511-12` | 005 | prueba de la primera regla; después, desarrollo | 23 / 13 |
| `0056-7` | 005 | prueba a ciegas | 3 / 9 |
| `00519-20` | 005 | prueba a ciegas | 28 / 24 |

Los archivos están en `data/gt_*.csv`.

## Resultados en colmenas conocidas

Modelo v5, configuración recomendada. Cada celda es eventos acertados / contados y F1.

| Video | Entradas | Salidas |
| :--- | :---: | :---: |
| `0040-1` (colmena 004) | 29 / 33, 0.84 | 45 / 46, 0.73 |
| `0031-2` (colmena 003) | 29 / 40, 0.75 | 14 / 25, 0.65 |

En el `0040-1` el F1 al azar es 0.29 en entradas y 0.38 en salidas.

Las reglas del contador se ajustaron con estos dos videos, así que estos números son de desarrollo, no de prueba.

En el `0040-1`, 33 de las 78 salidas se pierden. La mayoría son abejas que el detector no ve en ninguna imagen: al despegar salen borrosas.

## Prueba a ciegas en una colmena nueva

**Pregunta:** ¿cuenta el sistema en una colmena que el modelo nunca vio, sin cargar fotos de su fondo?

**Método** (*leave-one-hive-out*):

- El modelo v7 se entrenó igual que el v5, pero sin ninguna imagen de la colmena 005.
- Las reglas del contador se ajustaron solo con videos de las colmenas 003 y 004.
- En cada video de prueba solo se eligió la posición del círculo, mirando la primera imagen.
- La versión se congeló (commit `cfe0bdc`) antes de correr. Se corrió una sola vez.
- El conteo a mano se abrió después de la corrida.

**Resultado** en dos videos de la colmena 005 nunca usados antes (`0056-7` y `00519-20`: 31 entradas y 33 salidas reales). El F1 al azar va de 0.01 a 0.28 según el video.

| Modelo | Entradas (de 31) | Salidas (de 33) |
| :--- | :---: | :---: |
| **v7: nunca vio la colmena** | 21 / 23, **0.78** | 20 / 28, **0.66** |
| v8: v7 + 50 fotos del fondo de la colmena | 24 / 25, 0.86 | 17 / 26, 0.58 |
| v5: vio la colmena en el entrenamiento | 25 / 28, 0.85 | 23 / 27, 0.77 |

Detección foto por foto en la misma colmena (349 fotos etiquetadas, umbral 0.5): v7 encuentra 94 de cada 100 abejas (recall 0.94), pero marca muchos puntos falsos del fondo (precisión 0.55, F1 0.70). El v5 obtiene F1 0.92.

**Lectura:**

- El sistema cuenta en una colmena nueva sin fotos de su fondo, muy por encima del azar, y queda por debajo del modelo que sí la conoce.
- Las salidas son el punto débil. Ni el modelo que conoce la colmena encuentra más de 7 de cada 10: el límite es el detector, no el contador.
- El v7 también rinde menos que el v5 en la colmena 003, que los dos conocen (entradas 0.60 contra 0.81). No toda la diferencia viene de no conocer la colmena.

### Qué aportó cada regla

Estas filas no son el resultado oficial: sirven para ver el efecto de cada regla en los mismos dos videos. Elegir la mejor fila después de ver la prueba sería seleccionar con la propia prueba.

| v7 | Entradas | Salidas |
| :--- | :---: | :---: |
| Sin reglas para colmenas nuevas | 24 / 33, 0.75 | 19 / 35, 0.56 |
| + puntos fijos repetidos (`--rep-s 60`) | 24 / 33, 0.75 | 20 / 24, 0.70 |
| + manchas fijas (`--in-max-age 3 --in-park-s 0.15 --park-s 0.9`): versión congelada | 21 / 23, 0.78 | 20 / 28, 0.66 |

- `--rep-s` quita 12 de 16 salidas falsas sin perder ninguna real.
- Las reglas de entradas quitan 7 de 9 entradas falsas, y también 3 de 24 reales.
- `--park-s` agrega 4 salidas falsas y no recupera ninguna. Quitarla necesita otra prueba a ciegas antes de poder afirmarlo.

Los errores de los videos de prueba no se revisaron uno por uno, para que sirvan otra vez con un modelo reentrenado.

## Límites

- **Una sola colmena nueva.** La prueba muestra que funciona en la colmena 005, no en cualquier colmena.
- **Poca muestra.** Son 2 minutos y 64 eventos: uno o dos eventos mueven el F1 unos 0.03.
- **Un solo anotador.**
- **Colmenas parecidas.** Todas vienen del mismo conjunto de datos y de la misma cámara.
- **Cámara fija.** El sistema supone que la piquera no se mueve en la imagen. Los videos de la colmena 006, grabados con la cámara en mano, no sirven para medir.

## Comparación con el artículo original

Leocádio et al. (BRACIS 2023) evalúan con YOLOv8x y dos trackers (ByteTrack y EuTrack):

- Detector: 2100 fotos de las seis colmenas repartidas en entrenamiento, validación y prueba. Las tres partes tienen las mismas colmenas.
- Conteo: totales de un video por colmena contra el *Pseudo*, con error relativo promedio (18% a 33% en salidas en el mejor caso).

Este proyecto usa un modelo mucho más chico (54 KB, pensado para una Raspberry Pi), mide evento por evento y separa una colmena completa para la prueba. Las dos evaluaciones no son comparables número a número.
