
# tetragonisca-vision-edgeai

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Edge Impulse](https://img.shields.io/badge/Platform-Edge%20Impulse-purple.svg)](https://edgeimpulse.com/)
[![Dataset DOI](https://img.shields.io/badge/Dataset-10.5281%2Fzenodo.10439007-green.svg)](https://zenodo.org/records/10439007)

Sistema de visión artificial en el borde (Edge AI) diseñado para detectar la actividad en la piquera de la abeja nativa sin aguijón Tetragonisca angustula (Jataí/Angelita/Señorita).

Este proyecto usa un proceso reproducible centrado en los datos que limpia, revisa y añade fondos a las imágenes para entrenar la red neuronal FOMO (Faster Objects, More Objects) en dispositivos pequeños y de bajo consumo.

---

## 1. Visión General

El monitoreo de la abeja nativa sin aguijón Tetragonisca angustula es relevante para la agricultura de precisión y la conservación ecológica. Los sistemas tradicionales basados en la nube o en arquitecturas de mayor complejidad (como YOLO estándar) suelen presentar limitaciones de memoria y dependencia de conectividad constante a internet. Además de la detección con Inteligencia Artificial, este proyecto integra un algoritmo local de seguimiento espacial (MOT) para el conteo de individuos.

Este repositorio resuelve el procesamiento bajo el marco BLERP (Bandwidth, Latency, Economics, Reliability, Privacy):

- **Ancho de Banda (Bandwidth):** Procesa y analiza las imágenes localmente en el dispositivo sin necesidad de transmitir streaming continuo de video en alta definición hacia servidores externos.
- **Latencia (Latency):** Ejecuta la inferencia y localización en milisegundos directamente en el hardware embebido, permitiendo una respuesta inmediata en el punto de captura.
- **Economía (Economics):** Reduce los costos de operación al eliminar la transferencia masiva de datos por red móvil o satelital, así como el pago por consumo de infraestructura de cómputo en la nube.
- **Fiabilidad (Reliability):** Permite un funcionamiento continuo e independiente de forma offline, operando con autonomía en entornos rurales sin conectividad a internet.
- **Privacidad (Privacy):** Mantiene los datos procesados localmente dentro del dispositivo, asegurando que la información visual y ambiental de la ubicación no sea expuesta ni transmitida a servidores de terceros.

### 🔗 Modelos Públicos en Edge Impulse
El proyecto está dividido en dos repositorios públicos en Edge Impulse para facilitar la experimentación:
- **Modelo Base (`tetragonisca-vision-edgeai-base`)**: [Ver Proyecto](https://studio.edgeimpulse.com/studio/1073834). Entrenado únicamente con los datos de la Colmena 004.
- **Modelo Evolutivo (`tetragonisca-vision-edgeai-multihive`)**: [Ver Proyecto](https://studio.edgeimpulse.com/studio/1108884). Proyecto iterativo donde se combinan múltiples colmenas (004, 005, 001, etc.) utilizando la función de *Versioning* para mantener el historial de mejoras.

## 2. Arquitectura del Pipeline MLOps

```text
┌──────────────────────────────────────────────────────────────────┐
│ 1. ADQUISICIÓN DE DATOS (Data Ingestion):                        │
│    Dataset Crudo de Zenodo (Colmena 004 - 004.zip)               │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. PROCESAMIENTO DATA-CENTRIC (scripts/preparar_dataset_004.py): │
│    • Respeta la división nativa: 250 Train / 50 Valid / 50 Test  │
│    • Audita imágenes y etiquetas YOLO                            │
│    • Genera e inyecta parches de fondo ("unknown")               │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. CARGA AUTOMATIZADA (Edge Impulse CLI Uploader):               │
│    Subida de datos etiquetados respetando los Splits             │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. ENTRENAMIENTO Y OPTIMIZACIÓN (Edge Impulse Studio):           │
│    Modelo FOMO cuantizado en INT8 listo para microcontroladores  │
└──────────────────────────────────────────────────────────────────┘
```

## 3. Estructura del Repositorio

```text
tetragonisca-vision-edgeai/
├── data/
│   ├── raw/                      # Descarga de datos crudos (Zenodo Colmena 004)
│   └── processed/                # Datasets procesados unificados para Edge Impulse
│       ├── train/                # Conjunto de entrenamiento con parches de fondo (unknown)
│       └── test/                 # Conjunto reservado de evaluación (Test set)
├── models/                       # Artefactos exportados para inferencia local
│   ├── fomo_tetragonisca_int8.lite # Modelo TensorFlow Lite cuantizado int8 (~53 KB)
│   ├── labels.txt                # Archivo de etiquetas ("Abeja")
│   └── model_tetragonisca.eim    # Binario ejecutable para Linux AARCH64 (Raspberry Pi 5)
├── scripts/                      # Pipeline MLOps de preparación de datos
│   ├── 01_preparar_train.py      # Limpieza de Colmena 004 e inyección de clase negativa
│   ├── 02_copiar_valid_a_train.py # Unificación del split de validación en train
│   ├── 03_preparar_test.py       # Preparación del conjunto reservado de pruebas
│   ├── 04_extraer_despegues.py   # Frames alrededor de cada salida anotada (requiere anotación)
│   └── 05_extraer_borrosas.py    # Frames con abejas en movimiento que el modelo no detecta (sin anotar)
├── src/                          # Tracker v2 (Kalman) y contadores (v2, cruces, híbrido)
├── bench/                        # Evaluación: comparar eventos, detecciones guardadas, banco de pruebas
├── tools/                        # Anotación de eventos, editor de cajas, renombrar etiquetas en Edge Impulse
├── docs/                         # Algoritmo de seguimiento y pendientes
├── main.py                       # Inferencia + tracker + conteo (video o cámara)
├── deployment.md                 # Despliegue en la Raspberry Pi 5
├── .gitignore                    # Reglas de exclusión para Git (datasets y temporales)
├── LICENSE                       # Licencia BSD 3-Clause
└── README.md                     # Portada e instrucciones principales del proyecto
```

## 4. Dataset Crudo y Metadatos Científicos

El proyecto utiliza el registro científico oficial de *Tetragonisca angustula* publicado por Leocádio et al. (2024):

| Parámetro | Especificación |
| :--- | :--- |
| **Fuente Oficial** | Repositorio Zenodo (DOI: [10.5281/zenodo.10439007](https://zenodo.org/records/10439007)) |
| **Especie** | *Tetragonisca angustula* (Jataí / Angelita / Señorita) |
| **Subconjunto** | Colmena 004 (Colmena artificial en entorno rural) |
| **Sensor de Captura** | Cámara SONY HDR-AS20 (1920 × 1080p, 60 fps) |
| **Anotaciones** | Formato YOLO Bounding Boxes |
| **Licencia Datos** | Creative Commons Atribución-NoComercial 4.0 (CC BY-NC 4.0) |

## 5. Instalación, Configuración y Ejecución

Para replicar el proceso actual de procesamiento local de datos y carga a Edge Impulse Studio, sigue este flujo de trabajo:

### Paso 1: Clonar el repositorio y preparar dependencias

```powershell
# Clonar el proyecto
git clone https://github.com/tu-usuario/tetragonisca-vision-edgeai.git
cd tetragonisca-vision-edgeai

# Instalar librería para manipulación de imágenes
pip install Pillow
```

### Paso 2: Descargar los datos crudos (Colmena 004)

```powershell
cd data/raw
curl.exe -L "https://zenodo.org/records/10439007/files/004%20-%20Object%20Detection.zip?download=1" -o "004 - Object Detection.zip"
Expand-Archive -Path "004 - Object Detection.zip" -DestinationPath "004_Object_Detection_Raw" -Force
cd ../..
```

### Paso 3: Preparar el conjunto de entrenamiento y balancear la clase negativa

Ejecuta el primer script del pipeline para consolidar la carpeta plana `data/processed/train/`, asignar la etiqueta vacía a la primera imagen alfabética e inyectar 50 parches de madera lisa (clase `unknown`):

```powershell
python scripts/01_preparar_train.py
```

### Paso 4: Anexar los datos de validación al conjunto de entrenamiento

Ejecuta el segundo script para copiar todas las imágenes y etiquetas .txt de la carpeta valid directamente dentro de data/processed/train/ (unificándolas para la estructura plana de Edge Impulse):

```powershell
python scripts/02_copiar_valid_a_train.py
```

### Paso 5: Preparar el conjunto reservado de prueba (Test)

Ejecuta el tercer script para copiar las imágenes y etiquetas de prueba a `data/processed/test/`:

```powershell
python scripts/03_preparar_test.py
```

### Paso 6: Crear el proyecto en Edge Impulse y cargar los datos con la CLI

1. **Iniciar sesión** en [Edge Impulse Studio](https://studio.edgeimpulse.com/) y seleccionar **Create new project**.
2. Ir a **Dashboard** > **Keys** y copiar la **API Key** de tu proyecto.
3. **Subir las imágenes de entrenamiento (`train`)** desde la terminal con la CLI oficial:
   ```powershell
   edge-impulse-uploader --api-key TU_API_KEY --category training --directory data/processed/train --dataset-format yolo-txt
   ```
4. Subir las imágenes reservadas de prueba (test):
5. Verificar etiquetas en Edge Impulse Studio:
   - Comprobar en la plataforma que tanto las imágenes de Training como las de Test conserven sus etiquetas correctamente.
   - Excepción esperada: Los 50 parches de madera lisa y la foto de muestra de la piquera limpia en Training no tendrán etiquetas de abejas por pertenecer a la clase negativa (`unknown`).
   - Corrección manual (si se requieren re-subidas):
     - Si alguna imagen pierde su etiqueta, eliminarla manualmente desde la interfaz gráfica de Edge Impulse.
     - Crear una carpeta auxiliar temporal que contenga las imágenes a corregir, sus archivos `.txt` de etiquetas y el archivo `classes.txt` con el texto `Abeja`.
6. Re-subida manual desde la interfaz web (sin CLI):
   - En el menú lateral, ir a Data acquisition > Upload data.
   - En Upload mode, seleccionar "Select individual files" y elegir los archivos de la carpeta auxiliar.
   - En Image label format, seleccionar "YOLO TXT".
   - En Upload into category, seleccionar la categoría correspondiente ("Training" o "Testing").

---

## 6. Ciclo de Iteración: Agregar un Nuevo Dataset

Este flujo de trabajo describe el proceso reproducible para incorporar un nuevo dataset de colmena (por ejemplo, la Colmena 005, 006, etc.) al proyecto **`tetragonisca-vision-edgeai-multihive`** en Edge Impulse, utilizando la función de *Versioning* para no perder las iteraciones anteriores.

### Paso 1: Guardar la versión actual del modelo (Versioning)

Antes de modificar cualquier dato, protege el estado actual del proyecto en Edge Impulse:

1. En el menú lateral izquierdo, desplázate hacia abajo y haz clic en **Versioning**.
2. Haz clic en **Store new version**.
3. Asigna un nombre descriptivo que incluya los datasets ya entrenados y las métricas obtenidas. Ejemplo:
   - **Nombre:** `v1`
   - **Descripción:** `Modelo entrenado con colmenas 004 y 005. F1-Score: 0.94, Precision: 1.00, Recall: 0.89.`
4. Haz clic en **Store version**.

> La versión guardada actúa como punto de restauración. Si los nuevos datos deterioran el modelo, puedes restaurar esta versión con un clic.

### Paso 2: Preparar la carpeta del nuevo dataset en `data/raw/`

Los scripts del pipeline buscan **todas** las carpetas `train`, `valid` y `test` que encuentren dentro de `data/raw/`. Para procesar **únicamente** el nuevo dataset:

1. **Mueve o elimina** el dataset anterior de `data/raw/` (por ejemplo, `004_Object_Detection_Raw` y su `.zip`).
2. Descomprime el nuevo dataset dentro de `data/raw/` con la convención de nombre:
   ```
   data/raw/005_Object_Detection_Raw/
   ├── train/
   ├── valid/   (o val/)
   └── test/
   ```
3. Si el nuevo dataset **no tiene una imagen sin abejas** (clase negativa de fondo), agrégala manualmente:
   - Edita una foto del fondo de la piquera (sin abejas visibles) usando cualquier editor de imágenes.
   - Nómbrala `000_fondo.jpg` y colócala dentro de la carpeta `train/` del nuevo dataset.
   - No necesitas crear un archivo `.txt` para ella; el script lo generará vacío automáticamente.
   - El nombre `000_fondo.jpg` garantiza que el script la tome como la **primera imagen alfabética** y genere los 50 parches de fondo a partir de ella.

### Paso 2.5 *(opcional)*: Recortar imágenes de datasets con cámara lejana

> **¿Cuándo aplicar este paso?** Solo cuando el nuevo dataset fue grabado con la cámara más lejos de lo habitual y las abejas se ven significativamente más pequeñas que en los datasets anteriores. Si las abejas se ven de un tamaño similar al de los otros datasets, **salta este paso**.

Al comprimir imágenes con mucho "paisaje" a los `320 × 320 px` del modelo, las abejas pierden definición y se convierten en manchas de pocos píxeles, lo que reduce drásticamente el **Recall**. La solución es **recortar (crop)** las imágenes para eliminar el paisaje sobrante antes de subirlas, de modo que las abejas ocupen la misma proporción que en los datasets cercanos.

#### A. Recortar las imágenes con FastStone Photo Resizer

1. Abrir **FastStone Photo Resizer** (descarga gratuita desde [faststone.org](https://www.faststone.org/FSResizerDetail.htm)).
2. En el panel izquierdo, navegar hasta la carpeta raíz del dataset (la que contiene `train/`, `valid/` y `test/`).
3. Marcar la casilla **"Include Sub-Folders"** (abajo del panel izquierdo) para que incluya las subcarpetas automáticamente.
4. Seleccionar todas las imágenes y hacer clic en **"Add =>"**.
5. **Configurar la carpeta de salida** (para no sobrescribir las originales):
   - Desmarcar *"Output folder same as Input folder"*.
   - Hacer clic en **Browse** (`...`) y crear una carpeta nueva (ej. `Dataset_recortado`).
   - Marcar **"Keep original folder structure"** para conservar la organización `train/`, `valid/`, `test/`.
6. Marcar **"Use Advanced Options (Resize...)"** y hacer clic en **Advanced Options**:
   - Ir a la pestaña **Crop** → activar **"Enable Crop"**.
   - Seleccionar **"In Pixels"** y configurar el ancho y alto del recorte. Ejemplo para un zoom de ~1.5x sobre imágenes de `1920 × 1080`:

     | Parámetro | Valor |
     | :--- | :---: |
     | Width | `1280` |
     | Height | `720` |
     | X (Left) | `260` |
     | Y (Top) | `100` |

   - Usar el ícono de lupa (Preview) para verificar que el recuadro de recorte esté centrado sobre la entrada de la colmena.
7. Hacer clic en **OK** y luego en **Convert**.

> **Nota:** Los valores de X, Y, Width y Height dependen de cada dataset. El objetivo es que, tras el recorte, las abejas se vean del **mismo tamaño** que en los datasets donde la cámara estaba cerca. Usar el Preview para verificar antes de procesar.

#### B. Corregir las etiquetas YOLO (`.txt`) con el script

Al recortar las imágenes, las coordenadas de los archivos `.txt` originales (formato YOLO) quedan **desfasadas**: las cajas apuntan a posiciones incorrectas y algunas abejas que quedaron fuera del recorte siguen apareciendo como etiquetas fantasma. **Subir los `.txt` viejos junto con las fotos recortadas arruina el entrenamiento.**

El script `scripts/fix_crop_labels.py` recalcula automáticamente todas las coordenadas y elimina las cajas de abejas que quedaron fuera del recorte:

1. Abrir el archivo `scripts/fix_crop_labels.py` y ajustar los parámetros de configuración al final del archivo para que coincidan con los valores usados en FastStone:
   ```python
   DATASET_DIR = r"data\raw\001_Object_Detection_Raw\Dataset"    # Carpeta con los .txt originales
   OUTPUT_BASE = r"data\raw\001_Object_Detection_Raw\Dataset_labels_corregidos"

   ORIG_W = 1920    # Ancho original de las fotos
   ORIG_H = 1080    # Alto original de las fotos
   CROP_X = 260     # Posición X (Left) del recorte en FastStone
   CROP_Y = 100     # Posición Y (Top) del recorte en FastStone
   CROP_W = 1280    # Ancho del recorte
   CROP_H = 720     # Alto del recorte
   ```

2. Ejecutar el script:
   ```powershell
   python scripts/fix_crop_labels.py
   ```

3. Los `.txt` corregidos se generan en la carpeta `Dataset_labels_corregidos/` con la misma estructura (`train/labels/`, `valid/labels/`, `test/labels/`).

4. **Reemplazar** los `.txt` viejos en las carpetas `labels/` del dataset recortado por los `.txt` corregidos generados en el paso anterior.

### Paso 3: Procesar el nuevo dataset con el pipeline local

Desde la carpeta raíz del proyecto, ejecuta los tres scripts en orden:

```powershell
# Script 1: Limpia data/processed/train/, copia las imágenes de train e inyecta 50 parches de fondo
python scripts/01_preparar_train.py

# Script 2: Anexa las imágenes de valid/ dentro de data/processed/train/
python scripts/02_copiar_valid_a_train.py

# Script 3: Limpia data/processed/test/ y copia las imágenes de test/
python scripts/03_preparar_test.py
```

> Los scripts 01 y 03 **limpian automáticamente** las carpetas `processed/train/` y `processed/test/` antes de copiar los nuevos datos. No habrá imágenes duplicadas del dataset anterior.

### Paso 4: Subir el nuevo dataset a Edge Impulse con la CLI

Desde la carpeta raíz del proyecto, reemplazando `TU_API_KEY` por la clave de tu proyecto (disponible en **Dashboard > Keys**):

```powershell
# Subir imágenes de entrenamiento
edge-impulse-uploader --api-key TU_API_KEY --category training --directory data/processed/train --dataset-format yolo-txt

# Subir imágenes de evaluación
edge-impulse-uploader --api-key TU_API_KEY --category testing --directory data/processed/test --dataset-format yolo-txt
```

### Paso 5: Configurar el Impulso (Create Impulse)

En el menú lateral de Edge Impulse Studio, ir a **Impulse Design > Create Impulse**:

1. **Image Data (Input Block):** `320 × 320 px` | Resize mode: `Fit shortest axis`.
2. **Processing Block:** `Image` (color depth: **RGB**).
3. **Learning Block:** `Object Detection (Images)` — seleccionar la variante **FOMO**.
4. Hacer clic en **Save Impulse**.

### Paso 6: Generar Características (Image DSP)

1. En el menú lateral, ir a **Image**.
2. En la pestaña **Parameters**, verificar que el color depth sea **RGB** y hacer clic en **Save parameters**.
3. Ir a la pestaña **Generate features** y hacer clic en **Generate features**.
4. Revisar el **Feature explorer** para verificar la separabilidad de las clases.

### Paso 7: Entrenar el Modelo (Object Detection)

1. En el menú lateral, ir a **Object Detection**.
2. Configurar los parámetros de entrenamiento:

   | Parámetro | Valor |
   | :--- | :---: |
   | Number of training cycles (Epochs) | `100` |
   | Learning rate | `0.0015` |
   | Training processor | `GPU` |
   | Data augmentation | ✅ Activado |
   | Validation set size | `20` % |
   | Batch size | `32` |
   | Profile int8 model | ✅ Activado |
   | Neural network architecture | `MobileNetV2 0.35` |

3. Hacer clic en **Start training**.
4. Al finalizar, revisar la **Confusion matrix** y las métricas de validación:

   | Métrica clave | Comportamiento esperado |
   | :--- | :--- |
   | **Precision** | Mantenerse en **1.00** (sin falsos positivos). Si baja, revisar los parches de fondo del nuevo dataset. |
   | **Recall** | Idealmente igual o superior al modelo anterior. Una caída pequeña (≤3%) es normal al agregar variabilidad. |
   | **F1-Score** | Referencia de mejora global entre versiones. |

### Paso 8: Evaluar en el conjunto de prueba (Model Testing)

1. En el menú lateral, ir a **Model testing**.
2. Hacer clic en **Classify all**.
3. Verificar que las métricas en datos no vistos (Precision, Recall, F1-Score) sean consistentes con las del conjunto de validación. Una brecha grande entre validación y test indica sobreajuste (*overfitting*).

### Paso 9: Descargar el modelo exportado (Deployment)

#### Modelo `.lite` (TensorFlow Lite — para inferencia en Python/PC)

1. En el menú lateral, ir a **Deployment**.
2. En la sección **Libraries**, seleccionar **TensorFlow Lite (int8)**.
3. Hacer clic en **Build** y descargar el archivo generado.
4. Reemplazar el archivo anterior en la carpeta `models/` del repositorio:
   ```
   models/fomo_tetragonisca_int8.lite   ← reemplazar con el archivo descargado
   ```

#### Modelo `.eim` (Edge Impulse Linux Runner — para Raspberry Pi 5 / Linux AARCH64)

1. En el menú lateral, ir a **Deployment**.
2. En la sección **Run your impulse locally**, seleccionar **Linux (AARCH64)**.
3. Hacer clic en **Build** y descargar el archivo `.eim`.
4. Reemplazar el archivo anterior en la carpeta `models/`:
   ```
   models/model_tetragonisca.eim        ← reemplazar con el archivo descargado
   ```

### Paso 10: Guardar la nueva versión del modelo (Versioning)

Una vez verificados los resultados en Model testing y descargados los modelos:

1. En el menú lateral, ir a **Versioning**.
2. Hacer clic en **Store new version**.
3. Asignar nombre y descripción con las métricas del nuevo modelo. Ejemplo:
   - **Nombre:** `v3`
   - **Descripción:** `Modelo entrenado con colmenas 004, 005, 001 y 003. F1-Score: 0.93, Precision: 1.00, Recall: 0.88.`

El ciclo queda completo. El workspace de Edge Impulse puede recibir el siguiente dataset cuando sea necesario.

---

## 7. Configuración del Impulso

Una vez cargadas y verificadas todas las muestras en **Data acquisition**, el siguiente paso es diseñar el pipeline de procesamiento de señal (DSP) y aprendizaje profundo (Learning Block) dentro de Edge Impulse Studio:

### Paso 1: Configurar el Impulso (Create Impulse)

En el menú lateral, ir a **Impulse Design** > **Create Impulse** y definir los siguientes bloques:

1. **Image Data (Input Block):**
   - **Image width:** `320` px
   - **Image height:** `320` px
   - **Resize mode:** `Fit shortest axis` (mantiene la relación de aspecto recortando el eje más corto).
2. **Processing Block:**
   - Seleccionar **Image** (profundidad de color **RGB**).
3. **Learning Block:**
   - Seleccionar **Object Detection (FOMO)** (diseñado para estimar centroides de objetos pequeños en dispositivos restringidos).
4. Guardar la configuración haciendo clic en **Save Impulse**.

### Paso 2: Generación de Características (Image DSP)

1. En el menú lateral, ingresar al submenú **Image**.
2. En la pestaña **Parameters**, verificar que la profundidad de color sea **RGB** y seleccionar **Save parameters**.
3. Pasar a la pestaña **Generate features** y hacer clic en el botón **Generate features**.
4. Inspeccionar la proyección en 2D (**Feature explorer**) para verificar la separabilidad espacial de las muestras.

### Paso 3: Entrenamiento del Modelo de Detección (FOMO)

1. En el menú lateral, ingresar al submenú **Object Detection**.
2. Configurar los parámetros de **Training settings**:
   - **Number of training cycles (Epochs):** `100`
   - **Learning rate:** `0.0015`
   - **Training processor:** `GPU`
   - Marcamos **Data augmentation**
3. Configurar los parámetros de **Advanced training settings**:
   - **Validation set size:** `20`
   - **Batch size:** `32`
   - Marcamos **Profile int8 model**
4. Verificamos que la **Neural network architecture** sea `MobileNetV2 0.35` (o la variante recomendada por el EON Tuner).
5. Hacer clic en **Start training**.
6. Una vez finalizado el entrenamiento, revisar la matriz de confusión (**Confusion matrix**) y las métricas de rendimiento (F1-Score y precisión en el conjunto de validación).

## 8. Resultados y Métricas de Entrenamiento (Training Output - Validation Set)

El rendimiento del modelo FOMO se evaluó en la fase de entrenamiento utilizando el conjunto de validación de Edge Impulse Studio (20% de los datos de entrenamiento):

### Matriz de Confusión (Validation Set)

| Clase Real \ Predicción | Background (Fondo) | Abeja | F1-Score |
| :--- | :---: | :---: | :---: |
| **Background (Fondo)** | **100.0%** | **0.0%** | **1.00** |
| **Abeja** | **12.8%** | **87.2%** | **0.93** |

### Resumen de Métricas de Entrenamiento (Validation Set)

| Métrica | Valor | Descripción |
| :--- | :---: | :--- |
| **Precision (Abeja)** | **1.00 (100%)** | Cero falsos positivos: todas las detecciones registradas como abejas fueron correctas. |
| **Recall (Abeja)** | **0.87 (87.2%)** | Capacidad de captura de abejas presentes (12.8% de falsos negativos por oclusión o ángulo). |
| **F1-Score (Abeja)** | **0.93 (93.0%)** | Balance armónico general entre Precisión y Sensibilidad. |
| **F1-Score (Fondo)** | **1.00 (100%)** | Discriminación perfecta de la textura de madera lisa sin abejas (`unknown`). |

### Análisis Técnico del Entrenamiento

1. **Eliminación Total de Falsos Positivos (Precision = 1.00):**
   - La inyección de los 50 parches de madera lisa con etiquetas vacías (*Data-Centric AI*) permitió a la red neuronal aprender a ignorar las vetas y texturas de la piquera.
2. **Sensibilidad y Oclusiones (Recall = 0.87):**
   - El 12.8% de falsos negativos responde a abejas que ingresaron en ángulos complejos o en bordes de la celda de salida de FOMO, un margen aceptable para muestreo temporal en microcontroladores de bajos recursos.

## 9. Resultados y Métricas de Evaluación Final (Model Testing Output - Test Set)

Posteriormente, se ejecutó una evaluación masiva en la pestaña **Model testing** (*Classify all*) sobre el conjunto reservado de prueba (*Testing set*), el cual contiene imágenes que el modelo **nunca vio durante el entrenamiento**:

### Resumen General del Modelo (Test Set)

- **Accuracy General:** **91.84%**

### Resumen de Métricas de Detección de Objetos (Test Set)

| Métrica | Valor | Porcentaje | Descripción |
| :--- | :---: | :---: | :--- |
| **Precision (non-background)** | **0.99** | **99.0%** | Alta precisión con mínimos falsos positivos en datos de prueba. |
| **Recall (non-background)** | **0.87** | **87.0%** | Sensibilidad estable: detecta el 87% de las abejas presentes. |
| **F1 Score (non-background)** | **0.93** | **93.0%** | Desempeño general robusto en el conjunto de evaluación reservado. |

### Análisis Técnico del Desempeño en Pruebas (*Testing*)

1. **Alta Capacidad de Generalización:**
   - La alta precisión de **0.99** y el **Recall** estable de **0.87** en datos no vistos demuestran que el modelo no sufre de sobreajuste (*overfitting*) al incorporar múltiples colmenas (001, 004 y 005) y generaliza de manera robusta en escenarios reales.
2. **Validación del Enfoque Data-Centric:**
   - El F1-Score final de **0.93** en la fase de testing confirma que el balanceo de los datasets y la inyección de parches de fondo continúan generando un modelo adecuado y estable para su despliegue local en dispositivos Edge AI.

### Historial de Evolución de Métricas (Test Set)

Para evaluar el impacto de agregar variabilidad al modelo, se registran las métricas obtenidas tras la incorporación progresiva de nuevos datasets. Estas iteraciones corresponden a las versiones guardadas en los proyectos públicos de Edge Impulse:

| Proyecto | Versión | Datasets Incluidos | Accuracy | Precision | Recall | F1-Score | Notas |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| [**`-base`**](https://studio.edgeimpulse.com/studio/1073834) | **Base** | Solo 004 | 100.00% | 1.00 | 0.90 | 0.95 | Excelente baseline, pero con riesgo de sobreajuste a una sola colmena. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v1** | 004 + 005 | 94.85% | 1.00 | 0.89 | 0.94 | El Recall baja ligeramente por la iluminación, pero sin falsos positivos. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v2** | 004 + 005 + 001 | 91.84% | 0.99 | 0.87 | 0.93 | El modelo aprende la variabilidad y generaliza en 3 colmenas distintas. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v3** | 004 + 005 + 001 + 003 | 95.94% | 1.00 | 0.88 | 0.93 | Alta generalización a 4 colmenas, recuperando 1.00 de precisión y subiendo accuracy. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v4** | v3 + 196 frames de despegues del video `0040-1` | 94.42% | 0.98 | 0.88 | 0.93 | Igual con abejas normales. Los despegues salen de la primera mitad del `0040-1`. Luego se quitaron para usar el `0040-1` completo como prueba. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v5** | v3 + 273 frames de abejas borrosas (44 videos de la 004), sin el `0040-1`. **480×480** | 96.60% | 1.00 | 0.89 | 0.94 | Test más difícil: incluye borrosas de 6 videos no vistos. Mejor F1 hasta ahora. |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v6** | Mismos datos que v5. **320×320** | 89.79% | 0.99 | 0.85 | 0.91 | Mismo test que v5: con 320 se pierden más abejas (recall 0.85 frente a 0.89). |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v7** | v5 **sin la colmena 005** (344 muestras de train y 50 de test desactivadas, incluidos sus 50 fondos). **480×480** | 91.49% | 0.98 | 0.89 | 0.93 | Prueba *leave-one-hive-out*: el modelo nunca vio la 005. Su test ya no tiene imágenes de la 005, así que no se compara directo con la v5. Las muestras siguen en el proyecto (desactivadas). |
| [**`-multihive`**](https://studio.edgeimpulse.com/studio/1108884) | **v8** | v7 + los **50 fondos de la colmena 005** (sin ninguna abeja de la 005). **480×480** | 98.94% | 1.00 | 0.88 | 0.94 | Prueba de la hipótesis de los fondos: ¿basta con fotos del fondo de una piquera nueva para quitar las salidas falsas? Su test no tiene imágenes de la 005, así que el F1 no responde eso; lo responde la corrida del `00517-18`. |

**480 frente a 320 (mismo test, mismos datos, mismos parámetros):** la resolución 480 detecta más abejas (recall 0.89 frente a 0.85) sin falsos positivos (precisión 1.00). Con 480 las abejas borrosas conservan más detalle al reducir el recorte de 1080 px. A cambio, el modelo hace ~2.25 veces más cálculo, así que hay que medir los FPS en la Raspberry Pi. La v5 y la v6 no se comparan directamente con la v3, porque su test incluye abejas borrosas.

**Etiqueta unificada (3 oct 2026).** Hasta la v3 las cajas tenían dos etiquetas: `Abeja` y `Abeja\r` (un `\r` de Windows en un `classes.txt`). `tools/renombrar_etiqueta_ei.py` renombró 13,373 cajas en 1,391 muestras y ahora hay una sola clase. Renombrar cajas pide una API key con rol **Admin**. Los `classes.txt` nuevos se escriben sin salto de línea.

**Abejas en vuelo (borrosas).** El modelo casi no detecta a las abejas que despegan, porque salen borrosas: la v4 tenía solo ~20 entre los 196 despegues. `scripts/05_extraer_borrosas.py` busca, en videos sin anotar, los frames donde algo se mueve cerca de la piquera y FOMO no lo detecta. Así salieron 273 frames útiles de 44 videos de la colmena 004, sin contar el `0040-1` ni el `00427-28`. Las imágenes de 6 videos (1.º, 8.º, 15.º, 22.º, 29.º y 36.º de la carpeta) van a *test*, separadas **por video** para que no haya frames casi iguales en train y test.

## 10. Ejecución Local y Monitoreo en Tiempo Real

El pipeline de inferencia y conteo local utiliza el modelo exportado TFLite para realizar predicciones directamente sobre fuentes de video en dispositivos locales, aplicando un módulo de **Seguimiento (Tracker)** y **Conteo basado en Región de Interés (ROI)**.

Para consultar los detalles de implementación del Algoritmo Húngaro, el filtro de oscilaciones y el conteo inferido, revisa el archivo técnico: **[Documentación del Algoritmo de Seguimiento](docs/TRACKING_ALGORITHM.md)**

### Uso del Pipeline de Inferencia

El script `main.py` levanta el modelo FOMO, establece la circunferencia virtual de la piquera, asocia las abejas con identificadores únicos y despliega un panel de información en vivo (HUD) con el conteo de eventos de **Entrada (IN)** y **Salida (OUT)**. Al terminar, la consola muestra un resumen con las entradas, las salidas, la velocidad y los archivos generados. La velocidad se lee en tres líneas:

| Línea | Qué significa |
| :--- | :--- |
| **Llegan** | Imágenes por segundo que manda la cámara o que trae el video. Es el ritmo que hay que alcanzar. |
| **Puede analizar** | Promedio de imágenes por segundo que el equipo alcanza a analizar (detección + tracking), sin contar la espera de la cámara ni la lectura del video. Es el promedio de la columna `FPS` del avance en consola. |
| **Analizó** | Imágenes por segundo que de verdad procesó, contando todo. Con cámara dice `en vivo: sí/no`; con video grabado, `al ritmo del video: sí/no`. |

Si no alcanzó el ritmo, aparece una **Nota** con la causa: el equipo analiza más lento de lo que llega; o, con video grabado, abrir cada imagen del video es lento (con cámara no pasa); o, con cámara, la cámara mandó menos imágenes (por ejemplo con poca luz).

Ejemplo en la Raspberry Pi 5 con la C930e (1280×720, modelo 480, `--no-output`): llegan 30 img/s, puede analizar ~95, analizó 30.0 → en vivo: sí. Con un video grabado a 60 fps (`0040-1`) analizó 44.8 img/s: no alcanza los 60 del video porque abrir cada imagen cuesta tiempo, pero eso no limita a la cámara.

```powershell
python main.py --video "examples/videos/0040-1.mp4" --roi-x 900 --roi-y 600 --roi-r 220 --show
```

**Configuración recomendada (5 oct 2026).** Modelo v5 (480×480) con el contador híbrido y las reglas de salidas fugaces, boca de la piquera y puntos quietos (`--static-s 2`):

```powershell
python main.py --video examples/videos/0040-1.mp4 --model models/fomo_borrosas_480_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --output video_conteo.mp4 --events eventos.csv
```

Para otra colmena hay que ubicar la piquera primero: correr con `--no-output --snapshot-every 30` y revisar en `snapshots/` que el círculo caiga sobre la boca de la piquera. Si el círculo tiene que ser más chico que el del `0040-1`, agregar `--track-scale 220` para que el tracker no parta una abeja en dos (ver [Argumentos](#argumentos-de-configuración)).

### Argumentos de Configuración:
- `--video`: Ruta al archivo de video o cámara en vivo (`0`, `/dev/video0`).
- `--roi-x`, `--roi-y`: Coordenadas del centro geográfico de la piquera.
- `--roi-r`: Radio en píxeles del círculo de conteo. El tracker v2 mide todas sus distancias en múltiplos de este radio.
- `--tracker`: `v2` (por defecto: Kalman + gating, independiente de resolución y FPS) o `v1` (EuTrack original).
- `--threshold`: Confianza mínima para crear una abeja nueva (por defecto `0.55`).
- `--assoc-threshold`: Confianza mínima para seguir una abeja ya rastreada (por defecto `0.35`, rescata detecciones borrosas).
- `--cam-width`, `--cam-height`, `--cam-fps`: Resolución y FPS pedidos a la webcam.
- `--crop-roi`: recorta un cuadrado (lado corto del frame) centrado en la ROI antes del modelo, igual que *Fit shortest axis* de Edge Impulse. Sin esta opción el frame completo se aplasta a 320×320.
- `--counter`: `v2` (una entrada/salida por track, por defecto) o `hibrido` (cuenta cada salida que cruza el borde y las entradas como v2). Ver [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--max-gate`, `--max-gate-tentative`, `--accel-std`, `--max-lost`, `--cancel-s`, `--proj-min-speed`: ajustes del tracker y del contador híbrido (en radios de la ROI y segundos).
- `--track-scale`: px que el tracker usa como unidad de distancia (por defecto, `--roi-r`). Sirve para achicar el círculo de conteo sin que el tracker parta una abeja en dos detecciones. Por ejemplo, `--roi-r 100 --track-scale 220` cuenta en un círculo chico y sigue a las abejas como con radio 220. Conviene que sea parecido al radio usado en el `0040-1` en relación al tamaño de la abeja.
- `--core`: con `--counter hibrido`, fracción del radio que es la boca de la piquera (p. ej. `0.5`). Una salida solo cuenta si la abeja pasó por ahí, y una entrada solo si llega ahí. Así no cuentan las guardianas que vuelan frente a la piquera y cruzan el borde del círculo. En el `0040-1` con `--flash-exits --cancel-s 1.0`, `--core 0.5` da IN 0.84 y OUT 0.72 (sin él, 0.87 y 0.69). Ver los resultados del `0031-2` en [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--flash-exits`: con `--counter hibrido`, cuenta también las salidas que FOMO solo ve en 1–3 frames (despegues borrosos) y deja de proyectar los tracks que se cierran. Estas salidas aparecen en el contador con ~1.5 s de retraso y con ID `-1` en el CSV. Ver [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--static-s`: con `--flash-exits`, descarta una salida si en su punto ya había una detección en los N segundos anteriores (recomendado `2`). Una abeja que se va no sale de donde ya había algo quieto: ese punto suele ser una sombra o una abeja parada que FOMO ve a ratos. Ver [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--rep-s`: con `--flash-exits`, descarta una salida fugaz que sale de un punto fijo repetido: un sitio del fondo que FOMO confunde con una abeja y que se enciende una y otra vez sin moverse (recomendado `60`). Sirve en una colmena que el modelo no conoce, sin fotos de su fondo. Ver [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--in-max-age`, `--in-park-s`: reglas contra las manchas fijas del fondo que FOMO confunde con abejas en una colmena nueva (valores probados: `3` y `0.15`). Quitan entradas falsas: no cuenta un track viejo ni uno que estaba quieto y salta a la piquera. En el examen a ciegas de la colmena 005 quitaron 7 de 9 entradas falsas y 3 de 24 reales. Ver [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md).
- `--park-s`: evita que una mancha quieta tape los despegues cercanos (necesita `--flash-exits`; valor probado: `0.9`). Forma parte de la configuración que dio el examen a ciegas de la colmena 005. El análisis por partes de ese examen sugiere que no ayuda (agregó 4 salidas falsas), pero quitarla es una decisión de desarrollo que necesita otro examen a ciegas.
- `--events`: CSV con cada evento IN/OUT (tiempo, ID, posición).
- `--show`: Muestra la ventana visual de OpenCV con rastreos interpolados.

### Banco de Pruebas del Tracker (`bench/`)
Para medir cambios del tracker sin la Raspberry Pi, `bench/make_scenarios.py` cachea las detecciones de FOMO del video `0040-1.mp4` en varios escenarios, entre ellos una simulación de webcam 640x480 filmando un monitor (keystone, desenfoque, ruido, JPEG, exposición larga). Luego `bench/run_bench.py` compara v1 y v2 entre escenarios (la referencia agregada disponible es el conteo *Pseudo* del paper, 42 IN / 85 OUT; ver [Validación del Conteo](#validación-del-conteo)):

```powershell
python bench/make_scenarios.py --video examples/videos/0040-1.mp4 --out bench/cache   # ~5 min, una sola vez
python bench/run_bench.py --cache bench/cache                                          # segundos
python test_tracker_v2.py                                                              # pruebas sintéticas
```

### Validación del Conteo

**Referencia publicada.** La Tabla 1 de Leocádio et al., *"Multiple Object Tracking in Native Bee Hives - Jataí"*, reporta para el video `0040-1` un conteo *Pseudo* (conteo humano asistido por su software EuTrack): **156 abejas, 85 salidas y 42 entradas**. Es lo mismo que registra `0040-1.txt` del dataset `004 - MOT`. La columna *RD* (remoción de duplicados) de esa tabla corresponde a la salida de sus algoritmos (BT: 8 OUT / 24 IN; ET: 5 OUT / 32 IN), **no** a un conteo real. El paper no aclara si *Pseudo* incluye los cruces de las abejas guardianas que revolotean en la piquera.

**Definición de evento de este proyecto.** Se cuentan solo las abejas que **realmente entran** a la colmena o **se van** de ella, sin guardianas ni abejas que se asoman y vuelven. Como no existe una referencia publicada con esa definición, la verdad de campo se construye anotando el video a mano:

```powershell
# 1. Anotar entradas/salidas reales (instrucciones y controles en el propio script)
python tools/anotar_eventos.py --video examples/videos/0040-1.mp4 --roi-x 900 --roi-y 600 --roi-r 220 --out data/gt_0040-1.csv

# 2. Generar los eventos del tracker y compararlos evento por evento
python main.py --video examples/videos/0040-1.mp4 --roi-x 900 --roi-y 600 --roi-r 220 --no-output --events eventos.csv
python bench/compare_events.py data/gt_0040-1.csv eventos.csv
```

**Verdad de campo propia.** `data/gt_0040-1.csv` es la anotación manual del minuto completo de `0040-1.mp4` con esa definición: **36 entradas y 78 salidas**. Como referencia, el *Pseudo* del paper da 42 / 85.

**Cómo medir.** `bench/compare_events.py` empareja cada evento del tracker con uno anotado del mismo tipo. Con la tolerancia por defecto (±1 s y sin mirar la posición), las salidas no se distinguen del azar: hay ~1.3 salidas por segundo, y eventos puestos en momentos aleatorios ya dan F1 ≈ 0.65. Por eso:

- La columna **F1 azar** da el F1 que se obtiene desplazando en el tiempo los mismos eventos del tracker. Un resultado vale solo si lo supera con claridad.
- Se usa la medición estricta: `--tol 0.5 --max-angle 40`, es decir, ±0.5 s y del mismo lado de la piquera (±40° alrededor de la ROI).

```powershell
python main.py --video examples/videos/0040-1.mp4 --model models/fomo_nuevo_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.6 --max-gate-tentative 1.2 --accel-std 80 --no-output --events eventos.csv
python bench/compare_events.py data/gt_0040-1.csv eventos.csv --start 30 --tol 0.5 --max-angle 40
```

**Para ajustar el tracker sin el video**, `bench/dump_detections.py` guarda las detecciones crudas de cada frame y `bench/replay_detections.py` corre el tracker y el contador sobre ellas en segundos. El resultado es idéntico en cualquier PC con el mismo archivo. `bench/detection_at_events.py` mide solo el detector: en cuántos frames alrededor de cada evento anotado hay una detección cerca.

**Resultados (4 oct 2026).** Modelo v4 con `--crop-roi`, segunda mitad del video (30–60 s, que el modelo no vio: 18 entradas, 38 salidas), detecciones del PC, medición estricta:

| Contador | F1 IN (azar) | Salidas acertadas | F1 OUT (azar) |
| :--- | :---: | :---: | :---: |
| `v2` por defecto | 0.64 (0.26) | 6 de 38 | 0.22 (0.15) |
| `hibrido --max-gate 0.6 --max-gate-tentative 1.2 --accel-std 80` | 0.58 (0.23) | 18 de 38 | 0.46 (0.26) |

- **Entradas:** claramente por encima del azar.
- **Salidas:** el contador híbrido casi triplica las acertadas, pero se pierde la mitad. Más de 150 combinaciones de parámetros del tracker no mejoran esto. La causa está en el detector: al despegar, la abeja sale borrosa y FOMO deja de verla. Con `--crop-roi`, el modelo ve en 3 o más de 13 frames solo al 58% de las abejas que salen.
- **PC y Linux** dan las mismas celdas con probabilidades distintas en ±0.05. Basta eso para mover el F1 de salidas entre 0.06 y 0.08, así que diferencias menores a eso entre configuraciones no son significativas con un solo minuto anotado.

**Resultados (5 oct 2026).** Minuto completo del `0040-1`, modelo v5 (480×480), detecciones del PC de Brayan, medición estricta. Los ajustes se eligieron con este mismo minuto:

| Configuración | Entradas bien / contadas (de 36) | F1 IN (azar) | Salidas bien / contadas (de 78) | F1 OUT (azar) |
| :--- | :---: | :---: | :---: | :---: |
| Modelo base (`fomo_tetragonisca`), ajustes del 4 oct | | 0.75 | | 0.44 |
| v5, tracker ajustado para 480 | 33 / 40 | 0.87 (0.31) | 37 / 80 | 0.47 (0.27) |
| + `--flash-exits` | 33 / 40 | 0.87 (0.31) | 48 / 61 | 0.69 (0.39) |
| + `--core 0.5 --cancel-s 1.0` | 29 / 33 | 0.84 (0.29) | 46 / 49 | **0.72 (0.40)** |

- **Por qué se perdían las salidas:** revisando las 78 una por una, la abeja que despega aparece en 1–2 frames como una mancha borrosa, a ~250 px entre un frame y otro. El tracker no crea un ID con eso. `--flash-exits` cuenta esas manchas (detalle en [TRACKING_ALGORITHM.md](docs/TRACKING_ALGORITHM.md)).
- **Lo que ninguna regla recupera:** 17 salidas que el modelo no detecta en ningún frame. Eso depende del detector o de la cámara (exposición corta).

**Segundo video: `0031-2` (colmena 003).** No tiene anotación propia, solo los totales *Pseudo* del paper, así que se comparan totales y no aciertos. Piquera en la punta del tubo: `--roi-x 855 --roi-y 465 --roi-r 100 --track-scale 220`.

| `0031-2` | Salidas | Entradas |
| :--- | :---: | :---: |
| *Pseudo* (paper) | 21 | 32 |
| ByteTrack (paper) | 73 | 76 |
| EuTrack (paper) | 100 | 121 |
| Este proyecto, configuración recomendada | 31 | 40 |

**Tercer video: `00517-18` (colmena 005), sin ajustar nada.** ROI en la boca del tubo: `--roi-x 1035 --roi-y 630 --roi-r 100 --track-scale 220`, con la configuración recomendada.

| `00517-18` | Salidas | Entradas |
| :--- | :---: | :---: |
| *Pseudo* (paper) | 16 | 30 |
| ByteTrack (paper) | 17 | 31 |
| EuTrack (paper) | 20 | 34 |
| Este proyecto | 20 | 23 |

En esta colmena, más tranquila, los trackers del paper ya funcionaban bien, y este proyecto queda parecido: 4 salidas de más y 7 entradas de menos.

En el `0040-1`, el paper reporta ByteTrack 29 salidas / 45 entradas y EuTrack 21 / 47; este proyecto cuenta 49 / 33 (46 y 29 correctas). Comparar totales sirve como referencia, pero no prueba aciertos: un total puede coincidir por casualidad. Ajustar más para llegar justo a 21/32 sería sobreajustar a ese video; los valores se confirman con un tercer video.

**Calibración por colmena.** ROI, `--core` y `--track-scale` dependen de cada piquera y se fijan mirando la imagen (y, en el despliegue, con un minuto etiquetado). El resultado de prueba tiene que medirse en otro minuto. En el `00517-18`, con la ROI del paper (`--roi-x 1032 --roi-y 700 --roi-r 180 --track-scale 220 --core 0.7`) el conteo fue 23 salidas / 32 entradas; como se calibró con el mismo minuto, no es una prueba independiente.

### Prueba de generalización (5 oct 2026)

**Colmenas en el entrenamiento.** Según el historial de versiones de Edge Impulse: v1 = 004 y 005, v2 suma la 001 y v3 suma la 003. Por eso el `0040-1`, el `0031-2` y el `00517-18` son videos nuevos de **colmenas conocidas**. Las únicas colmenas que el modelo nunca vio son la **002** y la **006**.

**`0020-1` (colmena 002), corrida ciega única.** ROI fijada solo mirando la imagen: `--roi-x 570 --roi-y 815 --roi-r 180 --track-scale 220 --core 0.7`, configuración recomendada sin `--static-s` (todavía no existía).

| `0020-1` | Salidas | Entradas |
| :--- | :---: | :---: |
| *Pseudo* (paper) | 7 | 11 |
| **Este proyecto, ciego** | **43** | **8** |
| Con `--static-s 2` (regla creada mirando este video, ya no es ciego) | 16 | 8 |

36 de las 43 salidas salían del cuerpo del tubo, fuera del círculo, y 24 de un mismo píxel: una sombra bajo el tubo que FOMO ve a ratos. Cuando el tracker pierde una abeja en la boca, salta a esa sombra y cuenta una salida. La regla `--static-s 2` es general (la misma para todos los videos). Con las detecciones guardadas (`bench/replay_detections.py`):

| Salidas con y sin `--static-s 2` | Sin | Con | *Pseudo* |
| :--- | :---: | :---: | :---: |
| `0040-1` (F1 OUT) | 49 (0.72) | 47 (0.72) | 85 |
| `0031-2` | 31 | 25 | 21 |
| `00517-18` (ROI del paper; detecciones con el recorte de la ROI anterior) | 22 | 18 | 16 |
| `0020-1` | 43 | 16 | 7 |

Las entradas no cambian en ningún video.

**`0062-2M` (colmena 006).** 960×540 a 30 fps, cámara en mano. Corrida ciega con `--roi-x 425 --roi-y 228 --roi-r 60 --track-scale 110 --core 0.6 --static-s 2`: 25 salidas / 42 entradas contra el *Pseudo* 15 / 17. En el segundo 9 la cámara se mueve y se acerca, y la boca queda en el borde del círculo. El sistema supone una cámara fija, así que este video (y los demás de la 006, todos en mano) no sirve para medir el conteo.

**`00517-18` con el modelo sin la colmena 005 (v7, *leave-one-hive-out*), corrida única.** Misma configuración para los dos modelos: `--roi-x 1032 --roi-y 700 --roi-r 180 --track-scale 220 --core 0.7 --static-s 2`.

| `00517-18` | Salidas | Entradas |
| :--- | :---: | :---: |
| *Pseudo* (paper) | 16 | 30 |
| v5 (vio la colmena 005) | 19 | 32 |
| **v7 (nunca vio la colmena 005)** | **34** | **31** |
| **v8 (v7 + 50 fotos del fondo de la 005, sin sus abejas)** | **19** | **36** |

Las entradas casi no cambian (31 contra 32), así que el detector reconoce a las abejas de una colmena nueva. Las salidas suben de 19 a 34: 26 son salidas fugaces y 18 de ellas salen de solo 4 puntos fijos del fondo, por ejemplo 8 veces de (753, 1035). Son falsos positivos del detector sobre un fondo que no conoce, el mismo tipo de error que la sombra del `0020-1`. Esos puntos reaparecen con más de 2 s de separación, así que `--static-s 2` no los filtra.

**v8: agregar solo fotos del fondo.** Con la v7 más las 50 fotos del fondo de la colmena 005 (ninguna abeja de la 005), las salidas bajan de 34 a 19, igual que la v5 que sí vio sus abejas (*Pseudo*: 16). Las entradas suben de 31 a 36 (*Pseudo*: 30). Esto confirma que las salidas falsas venían del fondo desconocido y que unas pocas fotos del fondo sin abejas bastan para corregirlas.

**Conclusión.** En las dos colmenas nuevas (`0020-1` y la 005 con el modelo v7), las **entradas** quedan cerca de la referencia y las **salidas** se inflan por falsos positivos del detector en puntos fijos del fondo. La v8 lo confirma: al instalar el sistema en una colmena nueva, la calibración debe incluir fotos del fondo de esa piquera sin abejas (clase negativa) y no solo ajustar la ROI.

Los siguientes pasos están en [`docs/PENDIENTES.md`](docs/PENDIENTES.md).
