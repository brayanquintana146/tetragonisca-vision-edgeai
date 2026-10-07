# Prueba sin trampa: modelo v7 en una colmena que nunca vio (7 oct 2026)

Modelos:
- **v7** `v7_fomo_sin005_480_int8.lite`: nunca vio la colmena 005 ni fotos de su fondo.
- **v8** `v8_fomo_sin005_confondo_480_int8.lite`: v7 + 50 recortes del fondo de la 005. Es "colmena nueva + fotos del fondo", no es ciega.
- **v5** `v5_fomo_borrosas_480_int8.lite`: vio la 005. Es el techo de referencia.
- Ninguno vio la colmena 002.

Las reglas y la lista de videos están en `PROTOCOLO.md`, escrito antes de contar.

## 1. Detección foto por foto en la 005

349 fotos etiquetadas, 1225 abejas, umbral 0.5 (el de Edge Impulse por defecto).

| Modelo | ¿Vio la 005? | Precisión | Recall | F1 | Detecciones falsas | Tipo |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| v7 | no | 0.55 | 0.94 | 0.70 | 947 | ciega |
| v8 | solo el fondo | 0.78 | 0.88 | 0.83 | 312 | colmena nueva + fotos del fondo |
| v5 | sí (entrenó con 299 de estas fotos) | 0.93 | 0.92 | 0.92 | 91 | referencia |

Con umbral 0.7 (el que usa el contador para crear una abeja): v7 F1 0.78, v8 0.85, v5 0.91.

Regla de acierto: la foto entra como en Edge Impulse (recorte central de 1080 px a 480×480). Una detección acierta
si su centro cae dentro de la caja etiquetada, con una celda (18 px) de margen. Una detección por abeja.
No se pudo confirmar la regla exacta de Edge Impulse; esta es estricta.
Límite: 401 abejas etiquetadas quedan fuera del recorte central y no se evalúan.

## 2. Conteo en videos nuevos de la 005

Ninguno de estos videos tiene conteo de referencia. Solo se pueden comparar los modelos entre sí.
Zona de entrada elegida mirando el primer cuadro; lo demás igual para todos (`--roi-r 100 --track-scale 220 --core 0.5`).
Cada celda es entradas / salidas.

### Grupo A: configuración actual, primera corrida (ciega para v7)

| Video | v7 | v8 | v5 |
| :--- | :---: | :---: | :---: |
| `0051-2` | 3 / 35 | 7 / 30 | 3 / 19 |
| `0058-9` | 16 / 18 | 10 / 20 | 7 / 7 |
| `00518-19` | 37 / 12 | 41 / 14 | 42 / 11 |

### Grupo B: videos apartados, primera corrida con cada configuración (ciega para v7)

| Video | v7 actual | **v7 mejorada** | v8 actual | v8 mejorada | v5 actual | v5 mejorada |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `0055-6` (38 s) | 10 / 23 | **10 / 12** | 4 / 25 | 4 / 11 | 4 / 12 | 4 / 12 |
| `00511-12` | 29 / 15 | **29 / 11** | 22 / 25 | 22 / 13 | 20 / 14 | 20 / 14 |
| `00521-22` | 23 / 26 | **23 / 22** | 18 / 25 | 18 / 17 | 12 / 20 | 12 / 20 |
| Suma de salidas | 64 | **45** | 75 | 41 | 46 | 46 |

Lectura:
- Con la mejora, las salidas de v7 quedan casi iguales a las de v5 (45 contra 46), sin usar ninguna foto del fondo.
- La mejora no cambia nada en v5 (el modelo que ya conoce el fondo): solo quita lo que parece un punto fijo.
- Las entradas no cambian con la mejora. v7 cuenta más entradas que v5 (62 contra 36). Sin conteo a mano no se sabe cuál acierta.
- **Esto todavía no prueba aciertos.** Son totales. Para decir "acierta" hace falta contar a mano uno de estos videos.

## 3. La mejora: puntos fijos repetidos

Un punto del fondo que el modelo confunde con una abeja se enciende siempre en el mismo sitio, una y otra vez.
Una abeja que despega no repite el sitio y no se queda quieta.
Regla (se aprende del propio video, sin fotos ni etiquetas): cada destello fuera de la piquera que no se movió deja
una marca en su sitio. Una salida fugaz no cuenta si su sitio ya tiene 2 marcas en el último minuto
(un destello quieto de 2 o más cuadros vale por 2), o si el propio destello estuvo quieto 2 o más cuadros.
Valores: `rep_s=60, rep_k=2, rep_w2=2, rep_self=True`. No se aplica a las salidas por cruce.

Se eligió SOLO con el `0040-1` (colmena 004, conteo a mano) y el `0031-2` (colmena 003):

| Video de desarrollo | Modelo | Antes | Después |
| :--- | :--- | :---: | :---: |
| `0040-1` salidas bien / contadas (de 78), F1 (azar) | v7 | 45 / 50, 0.70 (0.34) | 45 / 50, 0.70 (0.34) |
| `0040-1` salidas bien / contadas (de 78), F1 (azar) | v5 | 45 / 47, 0.72 (0.39) | 45 / 46, 0.73 (0.38) |
| `0040-1` entradas bien / contadas (de 36), F1 (azar) | v7 | 25 / 32, 0.74 (0.30) | igual |
| `0031-2` salidas / entradas (Pseudo 21 / 32) | v7 | 23 / 36 | 19 / 36 |
| `0031-2` salidas / entradas (Pseudo 21 / 32) | v5 | 25 / 40 | 25 / 40 |
| `0040-1` + 4 puntos falsos puestos a propósito: salidas falsas | v7 | 25.6 | 9.0 |

No pierde ninguna salida real del `0040-1`. Con puntos falsos inyectados, quita dos tercios de las salidas falsas.

## 4. Videos de desarrollo con referencia (no son pruebas ciegas)

Estos dos videos ya se habían usado antes para calibrar. La regla nueva no se ajustó con ellos, pero la idea salió
de la falla que se vio en el `00517-18`. Configuración de siempre para ellos: `--roi-r 180 --core 0.7`.
Cada celda es entradas / salidas.

| Video | Colmena | Referencia Pseudo | v7 actual | **v7 mejorada** | v8 actual | v8 mejorada | v5 actual | v5 mejorada |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `00517-18` | 005 | 30 / 16 | 31 / 34 | **31 / 16** | 36 / 19 | 36 / 14 | 32 / 19 | 32 / 18 |
| `0020-1` | 002 (nadie la vio) | 11 / 7 | 10 / 9 | **10 / 8** | 14 / 9 | 14 / 6 | 8 / 16 | 8 / 9 |

## 5. Tabla resumen

| Modelo | Colmena | ¿El modelo vio esta colmena? | Resultado | Tipo |
| :--- | :--- | :--- | :--- | :--- |
| v7 | 005, fotos | no | detección F1 0.70 (recall 0.94, precisión 0.55) | ciega |
| v8 | 005, fotos | solo el fondo | detección F1 0.83 | colmena nueva + fotos del fondo |
| v5 | 005, fotos | sí | detección F1 0.92 | referencia |
| v7 | 005, grupo A | no | salidas 35 / 18 / 12 contra 19 / 7 / 11 de v5 | ciega, sin referencia |
| v7 mejorada | 005, grupo B | no | salidas 12 / 11 / 22 contra 12 / 14 / 20 de v5 | ciega, sin referencia |
| v7 actual | 005, grupo B | no | salidas 23 / 15 / 26 | ciega, sin referencia |
| **v7 mejorada** | 005, `00511-12` contado a mano | no | entradas F1 0.73 (azar 0.14), salidas F1 0.58 (azar 0.14) | **ciega, con conteo a mano** |
| v7 actual | 005, `00511-12` contado a mano | no | entradas F1 0.73 (azar 0.14), salidas F1 0.50 (azar 0.12) | ciega, con conteo a mano |
| v8 mejorada | 005, `00511-12` contado a mano | solo el fondo | entradas F1 0.71 (azar 0.13), salidas F1 0.69 (azar 0.12) | colmena nueva + fotos del fondo |
| v5 | 005, `00511-12` contado a mano | sí | entradas F1 0.88 (azar 0.16), salidas F1 0.81 (azar 0.16) | referencia |
| v8 mejorada | 005, grupo B | solo el fondo | salidas 11 / 13 / 17 | colmena nueva + fotos del fondo |
| v7 mejorada | 005, `00517-18` | no | 31 entradas / 16 salidas (Pseudo 30 / 16) | desarrollo |
| v7 actual | 005, `00517-18` | no | 31 / 34 | desarrollo |
| v7 mejorada | 002, `0020-1` | no | 10 / 8 (Pseudo 11 / 7) | desarrollo |
| v5 mejorada | 002, `0020-1` | no | 8 / 9 (Pseudo 11 / 7) | desarrollo |
| v7 | 004, `0040-1` | sí | entradas F1 0.74 (azar 0.30), salidas F1 0.70 (azar 0.34) | desarrollo |
| v5 mejorada | 004, `0040-1` | sí | entradas F1 0.84 (azar 0.29), salidas F1 0.73 (azar 0.38) | desarrollo |

## 6. Aciertos evento por evento en la 005: conteo a mano del `00511-12`

Brayan contó a mano el `00511-12` (grupo B) el 7 oct 2026: **23 entradas y 13 salidas** (`data/gt_00511-12.csv`).
Los eventos del programa ya estaban guardados antes de ese conteo y no se volvieron a correr.
Medición estricta: `bench/compare_events.py --tol 0.5 --max-angle 40 --roi-x 1065 --roi-y 640`.

| Modelo | ¿Vio la 005? | Entradas bien / contadas (de 23) | F1 entradas (azar) | Salidas bien / contadas (de 13) | F1 salidas (azar) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| v7, configuración actual | no | 19 / 29 | 0.73 (0.14) | 7 / 15 | 0.50 (0.12) |
| **v7, con la mejora** | no | 19 / 29 | **0.73 (0.14)** | 7 / 11 | **0.58 (0.14)** |
| v8, configuración actual | solo el fondo | 16 / 22 | 0.71 (0.13) | 9 / 23 | 0.50 (0.10) |
| v8, con la mejora | solo el fondo | 16 / 22 | 0.71 (0.13) | 9 / 13 | 0.69 (0.12) |
| v5 (con y sin la mejora) | sí | 19 / 20 | 0.88 (0.16) | 11 / 14 | 0.81 (0.16) |

Lectura:
- v7 cuenta en una colmena que nunca vio, muy por encima del azar, sin fotos del fondo.
- La mejora le quitó 4 salidas falsas y ninguna real (a v8, 10 falsas y ninguna real).
- Todavía no llega a v5: a v7 le sobran 10 entradas falsas y 4 salidas falsas, y se le escapan 6 salidas de 13.
  Los totales parecidos a los de v5 escondían eso.
- Es un solo minuto con 36 eventos: uno o dos eventos mueven el F1 unos 0.05.
- Este conteo sirve solo para medir. No se usa para ajustar el tracker (regla a).
- El conteo fue a ciegas: Brayan dijo que antes de contar solo vio el video de la herramienta de anotación,
  no el clip con lo que contó el programa.
- Comprobación de que el archivo es de este video: sus marcas coinciden con los eventos de v5 en el `00511-12`
  (19 de 20 entradas) y no con los del `00521-22` (2 de 12, nivel de azar).

## 7. Segunda ronda de mejoras (solo con `0040-1` y `0031-2`)

Brayan contó a mano el `0031-2` (colmena 003): 37 entradas y 18 salidas, sin guardianas, marcando al cruzar el círculo.
También contó de nuevo el `0040-1`: sus dos conteos coinciden en 110 de 112 eventos (36 / 78 y 35 / 77).

Causa encontrada y reproducida sin tocar la 005: las manchas fijas del fondo quedan como tracks quietos, saltan a la
abeja que aparece en la piquera (entrada falsa) y tapan los despegues cercanos. Con 4 manchas inyectadas en el
`0040-1` aparecen ~10 entradas falsas y se pierden ~7 salidas reales.

Reglas nuevas: `--in-max-age 3` y `--in-park-s 0.15` (entradas) y `--park-s 0.9` (salidas).
Cada celda es bien / contadas y F1. "Antes" ya incluye `--rep-s 60`.

| Video de desarrollo | Modelo | Entradas antes | Entradas después | Salidas antes | Salidas después |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `0040-1` | v7 | 25 / 32, 0.74 | igual | 45 / 50, 0.70 | igual |
| `0040-1` | v5 | 29 / 33, 0.84 | igual | 45 / 46, 0.73 | igual |
| `0031-2` | v7 | 20 / 36, 0.55 | 20 / 30, 0.60 | 10 / 19, 0.54 | igual |
| `0031-2` | v5 | 29 / 40, 0.75 | 29 / 35, 0.81 | 14 / 25, 0.65 | igual |
| `00511-12` (005, ya con respuesta conocida) | v7 | 19 / 29, 0.73 | 18 / 22, 0.80 | 7 / 11, 0.58 | 7 / 12, 0.56 |

Dato nuevo: v7 es peor que v5 también en la colmena 003, que los dos conocen (entradas 0.60 contra 0.81).
No toda su desventaja en la 005 viene de no conocerla.

## 8. Examen final a ciegas en la colmena 005

- Videos `0056-7` y `00519-20`: nunca usados, contados a mano por Brayan (3 + 28 entradas, 9 + 24 salidas).
- Reglas congeladas en el commit `cfe0bdc` antes de correr. Una sola corrida. El conteo a mano se abrió después.
- Examen único: los errores no se analizaron uno por uno, para no contaminar futuras pruebas.
- Medición estricta (±0.5 s y mismo lado). Los dos videos sumados. Cada celda es bien / contadas y F1.
  El F1 al azar va de 0.01 a 0.28 según el video.

**Resultado oficial: la configuración congelada.**

| Modelo | ¿Vio la 005? | Entradas (de 31) | Salidas (de 33) |
| :--- | :--- | :---: | :---: |
| **v7** | no | 21 / 23, **0.78** | 20 / 28, **0.66** |
| v8 | solo el fondo | 24 / 25, 0.86 | 17 / 26, 0.58 |
| v5 | sí | 25 / 28, 0.85 | 23 / 27, 0.77 |

Análisis por partes. **No es el resultado oficial**: sirve solo para ver qué aportó cada regla. Elegir la mejor
fila después de ver el examen sería seleccionar con el propio examen.

| Modelo | Configuración | Entradas (de 31) | Salidas (de 33) |
| :--- | :--- | :---: | :---: |
| v7 | del 5 oct (antes de hoy) | 24 / 33, 0.75 | 19 / 35, 0.56 |
| v7 | + `--rep-s 60` | 24 / 33, 0.75 | 20 / 24, 0.70 |
| v8 | del 5 oct | 24 / 32, 0.76 | 18 / 45, 0.46 |
| v5 | del 5 oct | 27 / 30, 0.89 | 23 / 26, 0.78 |

Por video, v7 con la configuración congelada:

| Video | Entradas bien / contadas / reales | F1 (azar) | Salidas bien / contadas / reales | F1 (azar) |
| :--- | :---: | :---: | :---: | :---: |
| `0056-7` | 2 / 3 / 3 | 0.67 (0.01) | 7 / 10 / 9 | 0.74 (0.09) |
| `00519-20` | 19 / 20 / 28 | 0.79 (0.25) | 13 / 18 / 24 | 0.62 (0.15) |

Tercer video del examen, `00523-24`, sin conteo a mano (solo totales, entradas / salidas con la congelada):
v7 26 / 23, v8 21 / 25, v5 22 / 20.

Lectura honesta:
- Lo que se puede afirmar: sin fotos del fondo, v7 saca F1 0.78 en entradas y 0.66 en salidas en una colmena que
  nunca vio. El modelo que sí la conoce, con las mismas reglas, saca 0.85 y 0.77.
- Ni el modelo que conoce la colmena pasa de 7 de cada 10 salidas: el límite ahí es el detector (despegues borrosos).
- Son dos minutos y 64 eventos: uno o dos eventos mueven el F1 unos 0.03.

Lo que sugiere el análisis por partes (es desarrollo, no resultado):
- `--rep-s 60` le quita a v7 12 salidas falsas (de 16 a 4) sin perder ninguna real.
- Las reglas de entradas le quitan a v7 7 de 9 entradas falsas, pero también 3 de 24 reales. A v5 le restan un poco.
- `--park-s` no recuperó ninguna salida y agregó 4 falsas a v7. Quitarla parece mejor, pero esa conclusión sale de
  mirar el examen. La versión "`--rep-s` sin `--park-s`" necesita otro examen a ciegas antes de poder citarla.

## 9. Lo que falta

- Más fotos de abejas borrosas en el entrenamiento: hoy todas son de la colmena 004. Agregar de la 003
  (nunca del `0031-2`, ni de la 005, la 002 o la 006, ni de videos contados a mano).
- Un modelo reentrenado puede dar este mismo examen con las mismas reglas congeladas.
- Videos de la 005 que siguen sin tocar: `0053-4`, `0054-5`, `0057-8`, `0059-10`, `00510-11`, `00513-14`,
  `00515-16`, `00520-21`, `00522-23`, `00524-25`.
- La memoria de 60 s solo se pudo probar con videos de un minuto.
- Videos de la 005 ya usados: grupo A, grupo B y `00517-18`. Quedan 13 sin tocar para pruebas futuras.

---

# Protocolo de la prueba sin trampa (escrito el 7 oct 2026, antes de contar)

## Modelos
- **v7** `v7_fomo_sin005_480_int8.lite`: nunca vio la colmena 005 ni fotos de su fondo. Prueba principal.
- **v8** `v8_fomo_sin005_confondo_480_int8.lite`: v7 + 50 recortes del fondo de la 005 (salen de la foto
  `0050-123`, sin abejas). Se reporta solo como "colmena nueva + fotos del fondo", nunca como ciega.
- **v5** `v5_fomo_borrosas_480_int8.lite`: vio la 005. Es el techo de referencia.
- Ninguno vio la colmena 002. La 006 no se usa (cámara en mano).

## Reglas
a. Los cambios al tracker/contador se desarrollan y validan SOLO con el `0040-1` (conteo a mano
   `data/gt_0040-1.csv`) y con videos de las colmenas conocidas 001/003/004. Nunca con videos de la 005 ni la 002.
b. Por video solo se elige la zona de entrada (centro de la boca del tubo), mirando el primer cuadro,
   antes de contar. Radio, escala y boca son los mismos para todos: `--roi-r 100 --track-scale 220 --core 0.5`.
c. La primera corrida de cada video con la configuración congelada es el resultado que se reporta.
   Todo lo que venga después se llama "desarrollo".
d. `00517-18` y `0020-1` ya se usaron para calibrar: son desarrollo, no pruebas ciegas.

## Videos de la 005
- Con fotos etiquetadas (v5 entrenó con cuadros de estos): `0050-1`, `00512-13`, `00525-26`, `00526-27`
  (train/valid) y `00514-15`, `00516-17` (test de Edge Impulse). No se usan para contar.
- `00517-18`: desarrollo. `0052-3`: apartado (no se sabe si ya se abrió antes).
- Quedan 19 videos sin usar. Elegidos por posición en la lista ordenada, sin mirar resultados:
  - **Grupo A** (configuración actual): `0051-2`, `0058-9`, `00518-19`.
  - **Grupo B** (después de las mejoras, no se tocan hasta congelar): `0055-6`, `00511-12`, `00521-22`.
  - Los otros 13 quedan de reserva.
- Solo `00517-18` trae conteo de referencia (Pseudo). Los demás no tienen referencia: hace falta contar a mano.

## Zona de entrada elegida (primer cuadro, antes de contar)
| Video | roi-x | roi-y |
| :--- | :---: | :---: |
| `0051-2` | 1110 | 590 |
| `0058-9` | 1110 | 585 |
| `00518-19` | 1060 | 640 |
| `0055-6` (grupo B) | 1110 | 590 |
| `00511-12` (grupo B) | 1065 | 640 |
| `00521-22` (grupo B) | 1135 | 565 |

## Configuración congelada (la recomendada del README, 5 oct 2026)
`--crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7
--max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0
--roi-r 100 --track-scale 220`

## Mejora congelada (antes de contar el grupo B)
Regla de "puntos fijos repetidos" en las salidas fugaces: `rep_s=60, rep_k=2, rep_w2=2, rep_self=True`.
Elegida solo con el `0040-1` (v7 y v5) y el `0031-2`, más puntos falsos inyectados en el `0040-1`.
No se aplica a las salidas por cruce (ahí perdía una salida real del `0040-1`).
En el grupo B se corre la configuración actual y la mejorada, las dos por primera vez.

## Segunda ronda de mejoras (7 oct 2026, después del conteo a mano del `00511-12`)
- `00511-12` ya tiene respuesta conocida: desde ahora es desarrollo para cualquier regla nueva.
  No se miran sus errores uno por uno para diseñar reglas.
- Desarrollo permitido: `0040-1` (v7 y v5) y `0031-2` (colmena 003). Para ver errores de "colmena
  desconocida" sin tocar la 005 ni la 002 se usa el modelo base del primer commit (solo vio la 004)
  sobre el `0031-2`: para ese modelo la 003 es una colmena nueva.
- Examen final a ciegas con v7: `0056-7` (1110, 590), `00519-20` (1065, 640) y `00523-24` (1075, 640),
  zona de entrada elegida del primer cuadro. No se corre nada en ellos ni se abre el conteo a mano
  de Brayan hasta congelar la versión final. Una sola corrida.

## Versión final congelada (commit `cfe0bdc`, antes de correr el examen)
Configuración recomendada del 5 oct + `--rep-s 60 --in-max-age 3 --in-park-s 0.15 --park-s 0.9`,
con `--roi-r 100 --track-scale 220 --core 0.5` y la zona de entrada de arriba.
Elegida con el `0040-1` y el `0031-2` (los dos contados a mano) y con manchas inyectadas en el `0040-1`.
El examen se corre una sola vez con v7, v8 y v5, y se guardan también la configuración del 5 oct y
la de `--rep-s 60` sola, para ver cuánto aporta cada ronda. Los conteos a mano de `0056-7` y
`00519-20` se abren después de la corrida.

## Detección foto por foto (regla fijada antes de mirar resultados)
Recorte central 1080 px -> 480x480 (como "Fit shortest axis"). Un centroide acierta si cae dentro de la
caja etiquetada ampliada una celda (18 px). Uno a uno. Umbral principal 0.5.
