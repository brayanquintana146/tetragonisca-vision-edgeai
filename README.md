# tetragonisca-vision-edgeai

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Edge Impulse](https://img.shields.io/badge/Platform-Edge%20Impulse-purple.svg)](https://edgeimpulse.com/)
[![Dataset DOI](https://img.shields.io/badge/Dataset-10.5281%2Fzenodo.10439007-green.svg)](https://zenodo.org/records/10439007)

Sistema de visión artificial en el borde (Edge AI) diseñado para detectar la actividad en la piquera de la abeja nativa sin aguijón Tetragonisca angustula (Jataí/Angelita/Señorita).

Este proyecto usa un proceso reproducible centrado en los datos que limpia, revisa y añade fondos a las imágenes para entrenar la red neuronal FOMO (Faster Objects, More Objects) en dispositivos pequeños y de bajo consumo.

---

## 1. Visión General

El monitoreo de la abeja nativa sin aguijón Tetragonisca angustula es clave para la agricultura de precisión y la conservación ecológica. Los sistemas tradicionales basados en la nube o en arquitecturas pesadas (como YOLO estándar) enfrentan colapsos de memoria y dependencia de conectividad constante a internet.

Este repositorio resuelve el problema operando bajo el marco BLERP (Bandwidth, Latency, Economics, Reliability, Privacy):

- **Ancho de Banda (Bandwidth):** Procesa y analiza las imágenes localmente en el dispositivo sin necesidad de transmitir streaming continuo de video en alta definición hacia servidores externos.
- **Latencia (Latency):** Ejecuta la inferencia y localización en milisegundos directamente en el hardware embebido, permitiendo una respuesta inmediata en el punto de captura.
- **Economía (Economics):** Reduce los costos de operación al eliminar la transferencia masiva de datos por red móvil o satelital, así como el pago por consumo de infraestructura de cómputo en la nube.
- **Fiabilidad (Reliability):** Garantiza un funcionamiento continuo e independiente de forma offline, operando con total autonomía en entornos rurales sin conectividad a internet.
- **Privacidad (Privacy):** Mantiene los datos procesados localmente dentro del dispositivo, asegurando que la información visual y ambiental de la ubicación no sea expuesta ni transmitida a servidores de terceros.

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

## 6. Configuración del Impulso

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

## 7. Resultados y Métricas de Entrenamiento (Training Output - Validation Set)

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
   - La inyección de los 50 parches de madera lisa con etiquetas vacías (*Data-Centric AI*) enseñó exitosamente a la red neuronal a ignorar las vetas y texturas de la piquera.
2. **Sensibilidad y Oclusiones (Recall = 0.87):**
   - El 12.8% de falsos negativos responde a abejas que ingresaron en ángulos complejos o en bordes de la celda de salida de FOMO, un margen sumamente aceptable para muestreo temporal en microcontroladores de bajos recursos.

## 8. Resultados y Métricas de Evaluación Final (Model Testing Output - Test Set)

Posteriormente, se ejecutó una evaluación masiva en la pestaña **Model testing** (*Classify all*) sobre el conjunto reservado de prueba (*Testing set*), el cual contiene imágenes que el modelo **nunca vio durante el entrenamiento**:

### Resumen General del Modelo (Test Set)

- **Accuracy General:** **100.00%**

### Resumen de Métricas de Detección de Objetos (Test Set)

| Métrica | Valor | Porcentaje | Descripción |
| :--- | :---: | :---: | :--- |
| **Precision (non-background)** | **1.00** | **100.0%** | Mantiene la ausencia total de falsos positivos en datos no vistos. |
| **Recall (non-background)** | **0.90** | **90.0%** | Incremento en la sensibilidad: detecta el 90% de las abejas presentes. |
| **F1 Score (non-background)** | **0.95** | **95.0%** | Desempeño global sobresaliente en el conjunto de evaluación reservado. |

### Análisis Técnico del Desempeño en Pruebas (*Testing*)

1. **Alta Capacidad de Generalización:**
   - La precisión perfecta de **1.00** y el incremento del **Recall** de **0.87 a 0.90** en datos no vistos demuestran que el modelo no sufrió de sobreajuste (*overfitting*) y generaliza de manera robusta en escenarios reales.
2. **Validación del Enfoque Data-Centric:**
   - El F1-Score final de **0.95** en la fase de testing confirma que el balanceo del dataset y la inyección de parches de fondo generaron una red neuronal sumamente confiable para su despliegue local en dispositivos Edge AI.
