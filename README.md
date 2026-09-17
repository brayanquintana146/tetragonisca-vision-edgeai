
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
│   └── model_tetragonisca.eim    # Binario ejecutable para Linux AARCH64 (Raspberry Pi)
├── scripts/                      # Pipeline MLOps de preparación de datos
│   ├── 01_preparar_train.py      # Limpieza de Colmena 004 e inyección de clase negativa
│   ├── 02_copiar_valid_a_train.py # Unificación del split de validación en train
│   └── 03_preparar_test.py       # Preparación del conjunto reservado de pruebas
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

#### Modelo `.eim` (Edge Impulse Linux Runner — para Raspberry Pi / Linux AARCH64)

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

## 10. Ejecución Local y Monitoreo en Tiempo Real

El pipeline de inferencia y conteo local utiliza el modelo exportado TFLite para realizar predicciones directamente sobre fuentes de video en dispositivos locales, aplicando un módulo de **Seguimiento (Tracker)** y **Conteo basado en Región de Interés (ROI)**.

Para consultar los detalles de implementación del Algoritmo Húngaro, el filtro de oscilaciones y el conteo inferido, revisa el archivo técnico: **[Documentación del Algoritmo de Seguimiento](docs/TRACKING_ALGORITHM.md)**

### Uso del Pipeline de Inferencia

El script `main.py` levanta el modelo FOMO, establece la circunferencia virtual de la piquera, asocia las abejas con identificadores únicos y despliega un panel de información en vivo (HUD) con el conteo de eventos de **Entrada (IN)**, **Salida (OUT)** y el total histórico de abejas.

```powershell
python main.py --video "examples/videos/0040-1.mp4" --roi-x 900 --roi-y 600 --roi-r 220 --show
```

### Argumentos de Configuración:
- `--video`: Ruta al archivo de video o cámara en vivo.
- `--roi-x`, `--roi-y`: Coordenadas del centro geográfico de la piquera.
- `--roi-r`: Radio en píxeles del círculo de conteo.
- `--threshold`: Umbral de confianza mínimo de la IA (por defecto `0.55`).
- `--show`: Muestra la ventana visual de OpenCV con rastreos interpolados.

### Precisión del Algoritmo (Prueba de Rendimiento)
Las calibraciones realizadas sobre secuencias biológicas reales confirmadas de forma manual por investigadores han arrojado los siguientes promedios de exactitud en situaciones de vuelo de alto tránsito:
- **Entradas (IN):** ~90% de exactitud (Bloqueo efectivo de falsos positivos en el tubo).
- **Salidas (OUT):** ~85% de exactitud (Restaurado por vectores de cinemática predictiva).
- **Conteo Acumulado:** Seguimiento de identidades únicas manteniendo el historial de la colonia.

> [!NOTE]
> **Validación Científica:** Según la investigación de Brasil *"Multiple Object Tracking in Native Bee Hives - Jataí"*, al aplicar su Filtro de Remoción de Duplicados (RD), el conteo biológico real es de **156 abejas totales, 42 entradas y 42 salidas**. Sin aplicar filtros (conteo bruto), los resultados biológicos arrojan 156 totales, 42 entradas y **85 salidas**. 
> Estos datos de campo se encuentran registrados oficialmente en el archivo `0040-1.txt` del dataset `004 - MOT`, del cual extrajimos el video de prueba original (`0040-1.mp4`). Los resultados del pipeline local (~38 IN, ~48 OUT, ~175 TOTAL) se aproximan a los resultados oficiales del filtro RD, procesándose en tiempo real en hardware de bajos recursos.
