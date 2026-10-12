# tetragonisca-vision-edgeai

[![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Edge Impulse](https://img.shields.io/badge/Platform-Edge%20Impulse-purple.svg)](https://edgeimpulse.com/)
[![Dataset DOI](https://img.shields.io/badge/Dataset-10.5281%2Fzenodo.10439007-green.svg)](https://zenodo.org/records/10439007)

Conteo de entradas y salidas de abejas nativas sin aguijón (*Tetragonisca angustula*: angelita, jataí, señorita) en la piquera de la colmena, con visión artificial en una Raspberry Pi 5 y sin conexión a internet.

Un detector FOMO de 54 KB encuentra las abejas en cada imagen. Un algoritmo de seguimiento las sigue de una imagen a la siguiente y cuenta cuántas entran y cuántas salen.

## Resultados

| Qué se midió | Resultado |
| :--- | :--- |
| Detección (test de Edge Impulse, modelo v5) | F1 0.94, precisión 1.00, recall 0.89 |
| Conteo en una colmena conocida (video `0040-1`, contado a mano) | Entradas F1 0.84, salidas F1 0.73 |
| Conteo en una colmena que el modelo nunca vio, sin fotos de su fondo (prueba a ciegas) | Entradas F1 0.78, salidas F1 0.66 |
| Velocidad en Raspberry Pi 5 con cámara a 30 fps | 30 imágenes por segundo, en tiempo real |

El conteo se mide evento por evento contra un conteo hecho a mano: cada entrada o salida del programa debe coincidir con una real en el tiempo (±0.5 s) y en el lado de la piquera. Contar al azar da un F1 entre 0.01 y 0.40 en estos videos.

El punto débil son las salidas: la abeja que despega aparece borrosa en una o dos imágenes y el detector no siempre la ve. El método, las tablas completas y los límites están en [docs/VALIDACION.md](docs/VALIDACION.md).

## Cómo funciona

```text
Cámara o video ─► Detector FOMO (480×480, int8) ─► Seguimiento (Kalman + Húngaro) ─► Contador ─► Entradas / Salidas
```

1. **Detección.** El modelo FOMO, entrenado en Edge Impulse, marca el centro de cada abeja.
2. **Seguimiento.** Cada abeja recibe un identificador que se mantiene mientras se mueve. Las distancias se miden en radios de la piquera y los tiempos en segundos, así que funciona igual con otra resolución o velocidad de cámara.
3. **Conteo.** Se dibuja un círculo sobre la piquera. Una abeja que cruza hacia dentro es una entrada y una que cruza hacia fuera es una salida. Varias reglas descartan a las guardianas que revolotean, los despegues que solo se ven una imagen y los puntos del fondo que el detector confunde con abejas.

El detalle de cada regla está en [docs/TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).

## Uso rápido

```powershell
git clone https://github.com/brayanquintana146/tetragonisca-vision-edgeai.git
cd tetragonisca-vision-edgeai
pip install -r requirements.txt
```

Contar en un video, con la configuración recomendada:

```powershell
python main.py --video examples/videos/0040-1.mp4 --model models/v5_fomo_borrosas_480_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --rep-s 60 --output video_conteo.mp4 --events eventos.csv
```

Al terminar, la consola muestra las entradas, las salidas y la velocidad. `--output` guarda el video anotado y `--events` un CSV con cada evento (tiempo, tipo y posición).

Opciones principales:

| Opción | Para qué sirve |
| :--- | :--- |
| `--video` | Archivo de video, o cámara (`0`, `/dev/video0`) |
| `--model` | Modelo `.lite` de la carpeta `models/` |
| `--roi-x`, `--roi-y`, `--roi-r` | Centro y radio, en píxeles, del círculo sobre la piquera |
| `--crop-roi` | Recorta un cuadrado centrado en la piquera antes del modelo, como en el entrenamiento |
| `--track-scale` | Tamaño de referencia de la abeja cuando el círculo es chico (por ejemplo `--roi-r 100 --track-scale 220`) |
| `--dashboard` | Página web con el conteo en vivo, en el puerto 5000 |
| `--no-output` | No guarda el video anotado (más rápido en la Raspberry Pi) |

`python main.py --help` lista todas las opciones.

**En una colmena nueva** solo hay que ubicar la piquera: correr con `--no-output --snapshot-every 30` y revisar en `snapshots/` que el círculo caiga sobre la boca. Para una colmena que el modelo no conoce se agregan `--in-max-age 3 --in-park-s 0.15 --park-s 0.9`, la configuración evaluada en la prueba a ciegas.

## Modelos

El nombre de cada archivo empieza con su versión en Edge Impulse.

| Versión | Datos de entrenamiento | Entrada | F1 (test) |
| :--- | :--- | :---: | :---: |
| v3 | Colmenas 001, 003, 004 y 005 | 320×320 | 0.93 |
| **v5** | v3 + 273 imágenes de abejas borrosas en vuelo | 480×480 | **0.94** |
| v7 | v5 sin la colmena 005 (para la prueba a ciegas) | 480×480 | 0.93 |

En el repositorio están la v3 y la v5 (`models/`). El historial completo y la guía para entrenar están en [docs/ENTRENAMIENTO.md](docs/ENTRENAMIENTO.md).

Proyectos públicos en Edge Impulse: [modelo base](https://studio.edgeimpulse.com/studio/1073834) (solo colmena 004) y [modelo multicolmena](https://studio.edgeimpulse.com/studio/1108884).

## Estructura del repositorio

```text
tetragonisca-vision-edgeai/
├── main.py        # Detección + seguimiento + conteo (video o cámara)
├── src/           # Seguimiento, contador, panel web
├── models/        # Modelos FOMO exportados (.lite)
├── bench/         # Evaluación: comparar eventos, guardar y repetir detecciones
├── tools/         # Anotar a mano entradas y salidas, editar cajas
├── scripts/       # Preparación de datos para Edge Impulse
├── data/          # Conteos a mano (gt_*.csv) y datos de entrenamiento
├── docs/          # Documentación
└── deployment.md  # Instalación en la Raspberry Pi 5
```

## Documentación

| Documento | Contenido |
| :--- | :--- |
| [docs/VALIDACION.md](docs/VALIDACION.md) | Cómo se midió el conteo, resultados y límites |
| [docs/TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md) | Algoritmo de seguimiento y reglas de conteo |
| [docs/ENTRENAMIENTO.md](docs/ENTRENAMIENTO.md) | Preparar datos, entrenar en Edge Impulse e historial de versiones |
| [deployment.md](deployment.md) | Instalación y uso en la Raspberry Pi 5 |
| [docs/PENDIENTES.md](docs/PENDIENTES.md) | Trabajo pendiente |

## Pruebas

```powershell
python test_counter_hybrid.py
python test_tracker_v2.py
```

## Datos

Se usa el conjunto de datos público de Leocádio et al. ([Zenodo, DOI 10.5281/zenodo.10439007](https://zenodo.org/records/10439007)): videos y fotos etiquetadas de seis colmenas de *Tetragonisca angustula*, grabados con una cámara SONY HDR-AS20 (1920×1080, 60 fps). Licencia de los datos: CC BY-NC 4.0.

> Leocádio, R. R. V., Segundo, A. K. R., Pessin, G. *Multiple Object Tracking in Native Bee Hives: A Case Study with Jataí in the Field*. BRACIS 2023. <https://doi.org/10.1007/978-3-031-45392-2_12>

## Licencia

Código bajo licencia [BSD 3-Clause](LICENSE).
