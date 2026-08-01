# Arquitectura de Seguimiento y Conteo (Tracking & Counting Algorithm)

El análisis del flujo de abejas en la piquera de *Tetragonisca angustula* presenta desafíos únicos para la visión por computadora: las abejas se cruzan constantemente a altas velocidades, oscilan o revolotean en la entrada sin decidirse a salir, y pueden aparecer borrosas debido a la limitación de cuadros por segundo de la cámara.

Para abordar esto, el sistema implementa un **Pipeline de Seguimiento y Conteo Adaptativo** robusto.

## 1. Algoritmo de Asociación Global (Algoritmo Húngaro)
El principal problema al rastrear enjambres es el "ID Switching" (intercambio de identidades). Los enfoques codiciosos tradicionales emparejan los centroides más cercanos de forma ingenua, lo cual falla estrepitosamente cuando dos o más abejas se cruzan, robándose mutuamente las identidades y corrompiendo las trayectorias.

Para resolver esto, se utiliza el **Algoritmo Húngaro** (`scipy.optimize.linear_sum_assignment`). Este algoritmo analiza una matriz de distancias globales entre todas las posiciones predichas y las nuevas detecciones en cada fotograma. En lugar de buscar la solución más óptima para la primera abeja, encuentra la asignación matemática que minimiza la distancia total del sistema, garantizando que los cruces y aglomeraciones no rompan las trayectorias individuales.

## 2. Cinemática Predictiva y Suavizado Adaptativo
Debido a la velocidad del vuelo de las Jataí, las detecciones por fotograma pueden estar muy distanciadas.

- **Predicción Vectorial de Velocidad:** Cuando FOMO falla en detectar una abeja durante uno o más fotogramas (micro-oclusión o desenfoque por movimiento rápido), el rastreador no congela su posición. En su lugar, avanza la posición esperada utilizando el último vector de velocidad válido conocido.
- **Amortiguación Fuerte:** Si una abeja desaparece repentinamente (ej. entra rápido al tubo), su velocidad predictiva se amortigua (se reduce al 40% en cada frame fantasma). Esto evita que el tracker "proyecte" trayectorias erróneas fuera del campo visual.
- **Suavizado Adaptativo (Alpha):** La interpolación entre la predicción y la nueva detección varía según la velocidad real de la abeja. Si la abeja camina lento, el suavizado es alto (trayectorias firmes); si vuela rápido, el suavizado es bajo (el tracker reacciona rápido para no quedarse atrás de la detección visual).

## 3. Lógica de Conteo Anti-Oscilaciones (Regla de Evento Único)
Las abejas guardianas y forrajeras suelen exhibir patrones de vuelo oscilatorio en el borde del ROI (Region of Interest). Cruzan la línea hacia afuera y hacia adentro repetidamente antes de decidir volar o aterrizar, inflando artificialmente los sistemas de conteo tradicionales.

Para neutralizar este fenómeno, se aplica una **arquitectura de bloqueo estricto**:
- Existe un conjunto en memoria de estado definitivo (`self.counted = set()`).
- En cuanto un ID registrado cruza la línea por primera vez (ya sea de adentro hacia afuera o viceversa), se incrementa el contador correspondiente y el ID queda sellado criptográficamente en el registro de contabilizados.
- Cualquier cruce posterior de esa misma abeja a lo largo del límite, sin importar si cambia de dirección, **se ignora por completo**. Solo un desplazamiento continuo, la pérdida total de visibilidad y el reingreso eventual con un nuevo ID restablecerá la posibilidad de un nuevo conteo.

## 4. Conteo Inferido Vectorialmente para Vuelos Veloces
Las Jataí que salen de la colmena suelen acelerar muy rápido desde el tubo hasta fuera del campo de visión. FOMO logra detectarlas en la base del ROI, pero a menudo se pierden antes de que su centroide cruce visiblemente la línea límite, perdiendo un conteo de "SALIDA (OUT)".

El sistema incorpora un **Conteo Inferido por Desaparición**:
- Cuando una abeja cruza el umbral de `max_disappeared` y el tracker la elimina oficialmente, se revisa su último instante *activo*.
- Si la trayectoria duró lo suficiente para descartar ruido temporal (`history_len >= 5`) y nunca fue contabilizada de forma directa por cruce visible, se examina su vector de velocidad final.
- Si el vector de velocidad apunta matemáticamente **hacia afuera** de la circunferencia del ROI en el momento de desaparecer, el sistema infiere un cruce exitoso e incrementa las Salidas (OUT). Lo mismo se aplica a las entradas en ángulo ciego (IN).
