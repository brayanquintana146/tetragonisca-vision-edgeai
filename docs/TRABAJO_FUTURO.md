# Trabajo futuro

Actualizado el 25 de noviembre de 2026.

La meta es que el sistema cuente bien en una colmena que el modelo nunca vio, sin cargar fotos de su fondo, y que funcione instalado en una colmena de Huyro. El estado actual está en [VALIDACION.md](VALIDACION.md). Los puntos van en orden de lo que más puede mejorar el conteo.

## 1. Entrenar el modelo v10 con más abejas borrosas

Es lo que más puede mejorar las salidas: el límite actual es el detector, que no ve bien a la abeja que despega. Hoy las 273 imágenes borrosas del entrenamiento son todas de la colmena 004.

| Colmena | Borrosas hoy | Videos para sacar | Estimado |
| :--- | :---: | :---: | :---: |
| 001 | 0 | 21 | 100 a 150 |
| 003 | 0 | 40 | 200 a 280 |
| 004 | 273 | ya usada | – |

Pasos:

1. Descomprimir `001 - MOT.zip` (36 videos).
2. Agregar a `scripts/05_extraer_borrosas.py` una opción de tamaño de recorte (ver "Colmena 001").
3. Sacar los cuadros de la 001 y la 003 y etiquetarlos en Edge Impulse. Apartar 5 o 6 videos completos de cada colmena para test: nunca cuadros del mismo video en train y en test.
4. Entrenar igual que el v7 (480×480, FOMO, con la colmena 005 desactivada) y exportar `models/v10_..._int8.lite`.
5. Pasar el v10 por la misma prueba a ciegas, con las mismas reglas congeladas.

Videos que **no** se usan para entrenar:

- Colmenas 005, 002 y 006 completas. La 005 es la colmena de prueba y la 002 se reserva como segunda colmena nueva.
- Videos contados a mano o usados en pruebas: `0040-1`, `00427-28`, `0031-2`.
- Los 15 videos de la 001 que traen conteo de referencia, que se apartan para desarrollo.

`--flash-exits` ya encuentra muchos despegues: esos cuadros también se pueden extraer y etiquetar para el mismo modelo.

### Colmena 001

- Sus fotos se recortaron antes de subirlas a Edge Impulse: de 1920×1080 a 1280×720 desde (260, 100). Las abejas quedaron 1.5 veces más grandes ([ENTRENAMIENTO.md](ENTRENAMIENTO.md), paso 2.5).
- Por eso, para sacar imágenes o contar en un video de la 001 hay que usar el mismo aumento: un cuadrado de 720 px alrededor de la piquera, no de 1080.
- La cámara se movió una vez. La boca del tubo queda cerca de (770, 285) en los primeros videos y cerca de (670, 460) en los últimos, en coordenadas del video original. Son valores aproximados: hay que fijar la posición video por video.

## 2. Contar a mano más videos

La prueba a ciegas actual son 2 minutos y 64 eventos. Orden sugerido:

1. `00523-24` (colmena 005): ya se corrió en la prueba; contarlo suma eventos (`--roi-x 1075 --roi-y 640 --roi-r 100`).
2. `0020-1` (colmena 002): primera medida evento por evento en la colmena que ningún modelo vio (`--roi-x 570 --roi-y 815 --roi-r 180`).
3. Videos de la 005 sin usar, para una segunda prueba: `0053-4`, `0054-5`, `0057-8`, `0059-10`, `00510-11`, `00513-14`, `00515-16`, `00520-21`, `00522-23`, `00524-25`.
4. Videos de la 002 sin usar (25), para una segunda colmena nueva.

Reglas al anotar: no contar guardianas, marcar cuando la abeja cruza el círculo y no mirar lo que contó el programa.

## 3. Repetir la prueba con otras colmenas

Hoy la evidencia es de una sola colmena nueva. Falta repetirla dejando fuera la 003 y la 004, y en la 002.

## 4. Decidir sobre `--park-s`

En la prueba a ciegas agregó salidas falsas y no recuperó ninguna. Quitarla necesita otra prueba a ciegas con videos del punto 2.

## 5. Instalación en la colmena

- Que `--events` guarde la hora real de cada evento y corte un archivo por día. Hoy guarda el segundo del video, que basta para medir pero no para seguir una colmena durante semanas.
- Conectar el conteo con el resto de la colmena inteligente (temperatura, humedad y peso), que lee el CSV de eventos para dar avisos al meliponicultor: por ejemplo, salidas que caen a cero con buen clima.
- Probar la cámara y la Raspberry Pi frente a una colmena real, varios días seguidos.

## 6. Código

- Pasar a `bench/` los scripts de la prueba a ciegas (detección foto por foto, conteo por grupos de videos, manchas inyectadas).
- `bench/make_scenarios.py` necesita TensorFlow en Windows.

## 7. Cámara

- Probar exposiciones más cortas en la C930e (`v4l2-ctl`, ver [deployment.md](../deployment.md)): si el despegue sale menos borroso, el detector lo ve más imágenes.
- La C930e graba a 30 fps y las reglas de salidas fugaces se ajustaron a 60 fps: revisar `max_hits` y `max_gap_s` con un video de esa cámara.

## Cómo probar sin sesgo

1. Las reglas del contador se ajustan solo con videos de desarrollo (`0040-1`, `0031-2`). Nunca con videos de prueba.
2. En cada video solo se elige la posición del círculo, mirando la primera imagen, antes de contar.
3. La versión se congela con un commit y se corre **una sola vez**. Ese es el resultado, aunque salga mal.
4. El conteo a mano se hace sin ver lo que contó el programa y se abre después de correr.
5. No se elige la mejor configuración después de ver la prueba.
6. Los errores de `0056-7`, `00519-20` y `00523-24` no se revisan uno por uno: así sirven otra vez con un modelo reentrenado.
7. Siempre se compara contra el F1 al azar.
