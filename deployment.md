# Guía de Despliegue en Raspberry Pi (Zero 2 W y 3 Model B+)

Este documento detalla los pasos para configurar y desplegar el modelo en dispositivos Raspberry Pi. Está diseñado para ser aplicable tanto en la **Raspberry Pi Zero 2 W** como en la **Raspberry Pi 3 Model B+**.

## 1. Preparación del Sistema Operativo (Flasheo de la MicroSD)

Para maximizar los recursos disponibles para la inferencia del modelo (especialmente en la Zero 2 W que tiene 512MB de RAM), utilizaremos una versión sin interfaz gráfica (Headless).

### Pasos Iniciales

1. **Abrir Raspberry Pi Imager**: Inicia el software Raspberry Pi Imager que ya tienes instalado en tu PC.
2. **Seleccionar Dispositivo**: En "Dispositivo", puedes seleccionar "Raspberry Pi Zero 2 W" (o la 3B+ según el caso) para filtrar los sistemas operativos compatibles.
3. **Seleccionar Sistema Operativo (OS)**:
   - Haz clic en **SO**.
   - Ve a **Raspberry Pi OS (other)**.
   - Selecciona **Raspberry Pi OS Lite (64-bit)** o **(32-bit)**. 
     - *Nota: El procesador de la Zero 2 W y la 3B+ soporta 64-bit. Se recomienda usar la versión Lite de 64-bit para mejor compatibilidad con ciertas librerías modernas de IA, a menos que el modelo específico o una librería (como versiones antiguas de tflite) exija 32-bit.*
4. **Seleccionar Almacenamiento**:
   - Haz clic en **Almacenamiento**.
   - Selecciona tu tarjeta MicroSD (¡Asegúrate de elegir la correcta para no borrar datos de tu PC!).
5. **Configuración Avanzada (OS Customisation)**:
   - Haz clic en el botón de engranaje (⚙️) o en "Next" para abrir los ajustes de personalización.
   - **General**:
     - Configura el **Nombre del equipo** (ej: `pizero` o `pi3`). En este caso el nombre será `pizero` para la Raspberry Pi Zero 2 W y `pi3` para la Raspberry Pi 3 Model B+.
     - Configurar la locaclización con la capital, la zona horaria y distrubución del teclado.
     - Habilita y configura un **nombre de usuario y contraseña** (ej: usuario `pi`, y una contraseña segura). En este caso la contraseña será `sihuyromelipo`.
     - Configura la **conexión Wi-Fi**. Configuraremos una Zona de cobertura inalambrica movil. El nombre de nuestra red será `MiLaptop-Net` y la contraseña también será `sihuyromelipo`, la banda de la red será 2.4 Ghz. 
   - **Services**:
     - Habilita **SSH** (Habilitar SSH y usar autenticación por contraseña). Esto es crucial para acceder a la Raspberry Pi de forma remota sin usar monitor ni teclado. Sobre Raspberry Pi Connect, no es necesario activarlo ahora porque todo funcionará en local.
6. **Escribir en la MicroSD**:
   - Guarda los ajustes y haz clic en **ESCRIBIR**.
   - Confirma que todos los datos en la tarjeta SD serán borrados.
   - Espera a que el proceso de escritura y verificación termine (puede tomar algunos minutos).

## 2. Primer Arranque y Conexión SSH

1. Retira la MicroSD de tu PC e insértala en la Raspberry Pi.
2. Conecta la Raspberry Pi a la fuente de alimentación.
3. Espera un par de minutos para que el sistema arranque y se conecte a tu red Wi-Fi por primera vez.
4. Abre una terminal en tu PC (PowerShell, CMD, o WSL) e intenta conectarte vía SSH:
   ```bash
   ssh tu_usuario@tu_hostname.local
   # Por ejemplo: ssh pi@pizero-edge.local
   ```
    En este caso para la pi zero usaremos `ssh pi@pizero.local` y para la pi 3 model b+ usaremos `ssh pi@pi3.local`. 

   *(Si el `.local` no funciona, es posible que necesites buscar la dirección IP de la Raspberry en la configuración de tu router y usar `ssh usuario@direccion_ip`)*.
5. Acepta la clave RSA (escribe `yes`) e ingresa tu contraseña.
## 3. Configuración del Entorno en la Raspberry Pi

Una vez que hayas ingresado por SSH, tendrás acceso a la terminal de la Raspberry Pi. Sigue estos pasos para preparar el sistema operativo y el entorno de Python.

### 3.1. Actualizar el Sistema
Es fundamental actualizar la lista de paquetes y el sistema operativo para asegurar que tienes los últimos parches y dependencias. Ejecuta:
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2. Preparar el Entorno Virtual de Python
Las versiones recientes de Raspberry Pi OS requieren el uso de entornos virtuales para instalar paquetes de Python, evitando así conflictos con el sistema.

1. Instala la herramienta para crear entornos virtuales:
   ```bash
   sudo apt install python3-venv -y
   ```
2. Crea un entorno virtual llamado `edgeai_env` (puedes elegir otro nombre si lo deseas):
   ```bash
   python3 -m venv ~/edgeai_env
   ```
3. Activa el entorno virtual. **Nota:** Deberás hacer este paso de activación cada vez que te conectes por SSH y quieras ejecutar el modelo.
   ```bash
   source ~/edgeai_env/bin/activate
   ```
   *(Sabrás que está activado porque tu terminal mostrará `(edgeai_env)` al principio de la línea).*

## 4. Transferencia de Archivos e Instalación de Dependencias

Una vez que el entorno de la Raspberry Pi está listo, debemos transferir los archivos necesarios desde la computadora y preparar las librerías.

### 4.1. Crear el directorio del proyecto
En la terminal de la Raspberry Pi (conectada por SSH), crea la carpeta donde vivirá el proyecto:
```bash
mkdir ~/tetragonisca-vision-edgeai
```

### 4.2. Transferir archivos desde la PC a la Raspberry Pi
En tu computadora, abre una **nueva terminal** (PowerShell o CMD) y asegúrate de estar en la carpeta raíz del proyecto. Ejecuta los siguientes comandos para enviar solo los archivos necesarios (evitando enviar datasets pesados como `data/` o carpetas de respaldo).

*Nota: Cambia `pizero.local` por `pi3.local` si estás usando la Raspberry Pi 3.*

```powershell
# 1. Enviar archivos principales
scp main.py requirements-pi.txt pi@pizero.local:~/tetragonisca-vision-edgeai/

# 2. Enviar código fuente
scp -r src pi@pizero.local:~/tetragonisca-vision-edgeai/

# 3. Enviar modelos
scp -r models pi@pizero.local:~/tetragonisca-vision-edgeai/
```

### 4.3. Instalar Dependencias
Vuelve a la terminal de la Raspberry Pi (asegúrate de tener activo el entorno virtual `edgeai_env`). Entra a la carpeta del proyecto e instala las librerías:

```bash
cd ~/tetragonisca-vision-edgeai
pip install -r requirements-pi.txt
```

## 5. Prueba de Inferencia Manual

Antes de automatizar todo, asegúrate de que el modelo corre correctamente en la Raspberry Pi.

1. Estando en la terminal SSH, asegúrate de tener el entorno activado (`source ~/edgeai_env/bin/activate`).
2. Ejecuta el script principal. En la Raspberry Pi, es recomendable usar el parámetro `--no-output` (para no guardar el video procesado y ahorrar CPU y disco).

```bash
# Si quieres procesar un video de prueba que subiste a la Pi:
python main.py --video 0040-1.mp4 --no-output --num-threads 4


# Si tienes una cámara conectada por USB (o la cámara oficial):
python main.py --video 0 --no-output --num-threads 4
```
3. Verifica en la terminal que el modelo carga (verás un mensaje de TensorFlow Lite XNNPACK) y que se imprimen los conteos. Presiona `Ctrl+C` para detenerlo.

## 6. Ejecución Automática al Arrancar (Autostart)

Para que la Raspberry Pi comience a contar abejas apenas la conectes a la corriente, crearemos un servicio de `systemd`.

1. Crea un archivo de servicio nuevo:
```bash
sudo nano /etc/systemd/system/bee-counter.service
```
2. Pega la siguiente configuración (ajusta `--video 0` o el número de tu cámara):
```ini
[Unit]
Description=Tetragonisca Bee Counter AI
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tetragonisca-vision-edgeai
ExecStart=/home/pi/edgeai_env/bin/python main.py --video 0040-1.mp4 --no-output --num-threads 4
Restart=always
RestartSec=10

# NOTA SOBRE USO EN PRODUCCIÓN: 
# Si bien puedes procesar videos ya grabados (ej: --video video_de_prueba.mp4), 
# la gran ventaja de Edge AI es procesar "en vivo" conectando la cámara (--video 0) 
# y usando el parámetro --no-output. Esto evita el desgaste de la memoria MicroSD 
# ya que la Raspberry analiza las imágenes en memoria RAM sin guardarlas, 
# emitiendo únicamente los conteos finales.
# Si vas a usar cámara en vivo, cambia "--video video_de_prueba.mp4" a "--video 0".
[Install]
WantedBy=multi-user.target
```
3. Guarda el archivo (`Ctrl+O`, luego `Enter`) y sal de nano (`Ctrl+X`).
4. Habilita e inicia el servicio con estos comandos:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bee-counter.service
sudo systemctl start bee-counter.service
```

### 6.1. Ver los registros (Logs)
Dado que el proceso corre en segundo plano de manera silenciosa, puedes revisar sus logs en tiempo real para verificar que sigue procesando cuadros y contando abejas:
```bash
sudo journalctl -u bee-counter.service -f
```
*(Presiona `Ctrl+C` para salir del visor de logs).*

### 6.2. Detener o Desactivar el Servicio
Si necesitas detener el modelo para hacer pruebas manuales o actualizar el código:
```bash
sudo systemctl stop bee-counter.service
```

Si deseas que no arranque automáticamente la próxima vez que conectes o reinicies la Raspberry Pi:
```bash
sudo systemctl disable bee-counter.service
```
*(Para volver a activarlo para producción, repite los comandos `enable` y `start` del paso 4).*

## 7. Consejos de Rendimiento, Registro y Control de Temperatura

Para llevar tu proyecto de Edge AI al siguiente nivel, puedes optimizar cómo se ejecuta el modelo. Estos parámetros aplican tanto al correrlo manualmente como al editar tu servicio de sistema (`bee-counter.service`).

* **Guardar un archivo CSV con el conteo:** Agrega `--log conteos.csv`. El sistema creará un archivo donde guardará el número de abejas por cada frame procesado para que luego puedas graficarlo en Excel.
* **Aumentar la velocidad (Saltar frames):** Agrega `--skip-frames 3`. Esto hará que la Raspberry Pi procese 1 cuadro de cámara y descarte los siguientes 2. Esto triplica la velocidad de inferencia (ideal para hardware pequeño) a costa de perder un poco de precisión en el rastreo de las abejas más rápidas.

### Control Avanzado de Temperatura (Taskset)
Por defecto, Linux y las librerías de IA intentarán usar todos los núcleos del procesador al mismo tiempo, lo que puede sobrecalentar la placa. Si quieres limitar la Inteligencia Artificial para que use solo 3 núcleos (dejando 1 núcleo 100% libre y frío para agregar sensores ambientales en el futuro), usa la herramienta nativa `taskset`:

```bash
taskset -c 0,1,2 python main.py --video 0 --no-output --num-threads 3 --skip-frames 2
```
Este comando encierra el proceso exclusivamente en los núcleos 0, 1 y 2, liberando totalmente el núcleo número 3.
