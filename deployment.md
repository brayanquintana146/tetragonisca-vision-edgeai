# Guía de Despliegue en Raspberry Pi 5

Este documento detalla los pasos para configurar y desplegar el modelo en dispositivos Raspberry Pi. Está diseñado para ser aplicable en la **Raspberry Pi 5**.

## 1. Preparación del Sistema Operativo (Flasheo de la MicroSD)

Para maximizar los recursos disponibles para la inferencia del modelo utilizaremos una versión sin interfaz gráfica (Headless).

### Pasos Iniciales

1. **Abrir Raspberry Pi Imager**: Inicia el software Raspberry Pi Imager que ya tienes instalado en tu PC.
2. **Seleccionar Dispositivo**: En "Dispositivo", puedes seleccionar "Raspberry Pi 5" para filtrar los sistemas operativos compatibles.
3. **Seleccionar Sistema Operativo (OS)**:
   - Haz clic en **SO**.
   - Ve a **Raspberry Pi OS (other)**.
   - Selecciona **Raspberry Pi OS Lite (64-bit)**. 
     - *Nota: El procesador de la Raspberry Pi 5 soporta 64-bit. Se recomienda usar la versión Lite de 64-bit para mejor compatibilidad con ciertas librerías modernas de IA.*
4. **Seleccionar Almacenamiento**:
   - Haz clic en **Almacenamiento**.
   - Selecciona tu tarjeta MicroSD (¡Asegúrate de elegir la correcta para no borrar datos de tu PC!).
5. **Configuración Avanzada (OS Customisation)**:
   - Haz clic en el botón de engranaje (⚙️) o en "Next" para abrir los ajustes de personalización.
   - **General**:
     - Configura el **Nombre del equipo** (ej: `pi5`). En este caso el nombre será `pi5` para la Raspberry Pi 5.
     - Configurar la locaclización con la capital, la zona horaria y distrubución del teclado.
     - Habilita y configura un **nombre de usuario y contraseña** (ej: usuario `pi`, y una contraseña segura). Elige una contraseña propia y no la escribas en este archivo.
     - Configura la **conexión Wi-Fi**. Configuraremos una Zona de cobertura inalambrica movil. El nombre de nuestra red será `MiLaptop-Net` con una contraseña propia (no la escribas aquí), la banda de la red será 2.4 Ghz. 
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
   # Por ejemplo: ssh pi@pi5.local
   ```
    En este caso usaremos `ssh pi@pi5.local`. 

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

*Nota: Utiliza `pi5.local`.*

```powershell
# 1. Enviar archivos principales
scp main.py requirements-pi.txt pi@pi5.local:~/tetragonisca-vision-edgeai/

# 2. Enviar código fuente
scp -r src pi@pi5.local:~/tetragonisca-vision-edgeai/

# 3. Enviar modelos
scp -r models pi@pi5.local:~/tetragonisca-vision-edgeai/

# 4. Enviar videos de prueba
scp -r examples pi@pi5.local:~/tetragonisca-vision-edgeai/
```

### 4.3. Instalar Dependencias
Vuelve a la terminal de la Raspberry Pi (asegúrate de tener activo el entorno virtual `edgeai_env`). Entra a la carpeta del proyecto e instala las librerías:

```bash
cd ~/tetragonisca-vision-edgeai
pip install -r requirements-pi.txt
```

> **Solución de problemas (Sin Internet / DNS):** Si al intentar instalar las librerías obtienes un error como `Temporary failure in name resolution`, significa que la Zona de Cobertura de Windows no le está compartiendo correctamente la dirección DNS a la Raspberry Pi. Para solucionarlo rápidamente inyectando el DNS de Google, ejecuta este comando y luego vuelve a intentar instalar:
> ```bash
> echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
> ```

## 5. Conexión de la Cámara y Prueba en Vivo

Antes de automatizar el sistema, haremos una prueba real con la cámara física.

### 5.1. Conexión Física (Apagado)
⚠️ **¡IMPORTANTE: REQUISITO DE ENERGÍA!** 
Al conectar una cámara y correr la IA, la Raspberry Pi 5 consumirá mucha energía (hasta 15W - 25W). Si estás dándole energía desde un puerto USB de la laptop, la placa **se apagará o reiniciará** apenas encienda la cámara.
*   Antes de conectar la cámara, **apaga la Raspberry Pi** y conéctala a un cargador de pared oficial o de buena calidad (mínimo 5V 3A).

1. **Si usas una Webcam (USB):** Simplemente conéctala a uno de los puertos USB azules (USB 3.0) de la Raspberry Pi.
2. **Si usas la cámara oficial (CSI/MIPI):** Conecta el cable plano flexible en el puerto `CAM/DISP` de la placa, asegurándote de que los pines metálicos toquen los contactos del conector.

### 5.2. Prueba de Inferencia Manual
1. Abre una terminal (como PowerShell) en tu computadora y conéctate a la Raspberry Pi por SSH. Una vez dentro, activa el entorno virtual y entra a la carpeta del proyecto. Los comandos exactos son:

```bash
ssh pi@pi5.local
# (Ingresa tu contraseña cuando el sistema te la pida)

source ~/edgeai_env/bin/activate
cd tetragonisca-vision-edgeai/
```
2. Ejecuta el script principal indicando el parámetro `--video 0` para activar la cámara en vivo. Generaremos un archivo de salida para que puedas descargarlo y verificar que el círculo se dibuja correctamente.

```bash
# Si quieres procesar un video de prueba que subiste a la Pi:
python main.py --video examples/videos/0040-1.mp4 --no-output --num-threads 4


# Si tienes una cámara conectada por USB (o la cámara oficial):
# Se pide explícitamente 640x480 a 30 fps. La ROI (--roi-x, --roi-y, --roi-r) va en píxeles
# de ESA resolución y debe rodear la piquera tal como aparece en la imagen de la cámara
# (no necesariamente el centro de la pantalla). Si el círculo se sale del frame, el script avisa.
python main.py --video 0 --cam-width 640 --cam-height 480 --cam-fps 30 \
  --roi-x 320 --roi-y 240 --roi-r 100 --num-threads 4 --snapshot-every 150
```

> **Calibrar la ROI con la cámara:** corre una vez con `--snapshot-every 150` y revisa las imágenes de `snapshots/`. El círculo amarillo debe cubrir la piquera con un margen de ~1 cuerpo de abeja. El tracker v2 mide todas sus distancias en radios de la ROI, así que un radio mal puesto afecta el conteo.

> **Ajustes de la webcam (Logitech C930e u otra UVC):** en poca luz la cámara alarga la exposición y baja a ~15 fps, y las abejas en vuelo salen borrosas (justo las salidas). Fija la exposición y apaga el autofoco, que "busca" constantemente sobre una pantalla. Los nombres de los controles cambian según el kernel: consulta primero `v4l2-ctl -d /dev/video0 --list-ctrls`. En Raspberry Pi OS Bookworm suelen ser:
> ```bash
> sudo apt install v4l-utils
> v4l2-ctl -d /dev/video0 -c auto_exposure=1 -c exposure_time_absolute=100 -c exposure_dynamic_framerate=0
> v4l2-ctl -d /dev/video0 -c focus_automatic_continuous=0 -c focus_absolute=0
> ```
> (`exposure_time_absolute` va en unidades de 100 µs: 100 = 10 ms. Súbelo si la imagen queda oscura.)
3. Mientras el modelo está corriendo, puedes monitorear el esfuerzo de la placa abriendo **otra ventana de PowerShell** y conectándote por SSH (`ssh pi@pi5.local`) para usar estas herramientas:
   * **Rendimiento (CPU y RAM):** Ejecuta `htop`. Verás barras que indican el trabajo del procesador. Presiona `q` para salir.
   * **Temperatura:** Ejecuta `watch -n 1 vcgencmd measure_temp`. Mostrará la temperatura en vivo (ideal <80°C). Presiona `Ctrl+C` para salir.

4. Verifica en la primera terminal que el modelo carga (verás un mensaje de TensorFlow Lite XNNPACK) y que se imprimen los conteos. Para **apagar la cámara y detener la IA**, simplemente presiona `Ctrl+C` en esa terminal.

5. **Visualizar el video procesado (Opcional):** Si quieres ver gráficamente cómo la IA detectó y contó las abejas dibujando las cajas sobre el video, corre el script omitiendo el parámetro `--no-output`. Al finalizar, se generará el archivo `output_result.mp4`. Para descargarlo a tu computadora y verlo, abre una terminal de PowerShell en tu PC (dentro de la carpeta del proyecto) y ejecuta:
```powershell
scp pi@pi5.local:~/tetragonisca-vision-edgeai/output_result.mp4 .
```
*(Reemplaza `pi5.local` por tu IP si es necesario, y no olvides el punto `.` al final).*

### 5.3. Apagado Seguro de la Raspberry Pi
⚠️ **¡Nunca desconectes el cable de energía de golpe!** Hacerlo puede corromper la memoria MicroSD y obligarte a reinstalar todo.

Para apagar la Raspberry Pi de forma segura al terminar tus pruebas o demostración, ejecuta este comando en la terminal SSH:
```bash
sudo shutdown -h now
```
*(Espera unos 10 segundos a que la luz verde de la placa deje de parpadear y se apague por completo antes de desenchufarla del tomacorriente).*

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
ExecStart=/home/pi/edgeai_env/bin/python main.py --video 0 --no-output --roi-x 320 --roi-y 240 --roi-r 100 --num-threads 4 --dashboard
Restart=always
RestartSec=10

# NOTA SOBRE USO EN PRODUCCIÓN / DEMOSTRACIÓN: 
# La Inteligencia Artificial arrancará procesando la cámara en vivo de forma silenciosa.
# Al incluir el parámetro --dashboard, podrás abrir el navegador en tu laptop 
# (estando en la misma red Wi-Fi) e ingresar a http://pi5.local:5000 
# para ver el conteo de abejas en tiempo real. ¡Ideal para demostraciones!
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
* **Aumentar la velocidad (Saltar frames):** Agrega `--skip-frames 3` al procesar **archivos de video**: la Raspberry Pi procesa 1 cuadro y descarta los 2 siguientes. Con **cámara en vivo** este parámetro se ignora: el programa lee la cámara en un hilo aparte y siempre procesa el frame más reciente, así que ya va a la máxima velocidad posible sin acumular retraso. Para contar bien las salidas conviene procesar **al menos ~15 fps efectivos** (revisa la línea `FPS:` de la consola).
* **Registrar cada entrada/salida:** Agrega `--events eventos.csv` (tracker v2). Guarda una fila por evento con el tiempo, el ID y la posición, útil para validar el conteo contra el video.

### 7.1. Monitoreo de Hardware en Tiempo Real
Mientras el modelo está en ejecución, es buena idea supervisar el estado de la placa (especialmente importante en una Raspberry Pi 5 sin disipador). Para esto, abre una **segunda conexión SSH** en otra ventana de tu terminal y utiliza estas herramientas:

1. **Uso de CPU y RAM (`htop`):**
   ```bash
   htop
   ```
   *Muestra un panel visual con el porcentaje de uso de los 4 núcleos del procesador y la cantidad de memoria RAM ocupada. Presiona `F10` o la letra `q` para salir.*

2. **Temperatura del Procesador:**
   ```bash
   watch -n 1 vcgencmd measure_temp
   ```
   *Refresca la temperatura de la placa cada 1 segundo. Vigila que no sobrepase los 80°C para evitar que el sistema se ralentice automáticamente. Presiona `Ctrl+C` para salir.*

### 7.2. Control Avanzado de Temperatura (Taskset)
Por defecto, Linux y las librerías de IA intentarán usar todos los núcleos del procesador al mismo tiempo, lo que puede sobrecalentar la placa. Si quieres limitar la Inteligencia Artificial para que use solo 3 núcleos (dejando 1 núcleo 100% libre y frío para agregar sensores ambientales en el futuro), usa la herramienta nativa `taskset`:

```bash
taskset -c 0,1,2 python main.py --video 0 --no-output --num-threads 3 --skip-frames 2
```
Este comando encierra el proceso exclusivamente en los núcleos 0, 1 y 2, liberando totalmente el núcleo número 3.

## 8. Migración de Hardware

El sistema operativo, las librerías de IA y todas tus configuraciones (incluyendo el servicio de autoarranque y contraseñas) residen en la tarjeta MicroSD. Esto hace que escalar o migrar el hardware sea extremadamente sencillo.

Si deseas mover tu proyecto de una placa anterior a una Raspberry Pi 5 para obtener más cuadros por segundo y menor temperatura, sigue estos pasos físicos:

1. Apaga la Pi de forma segura: `sudo shutdown -h now`.
2. Desconecta la corriente, extrae la MicroSD y ponla en la nueva Raspberry Pi.
3. Conéctala a la corriente. El sistema booteará idéntico, reconociendo el nuevo hardware automáticamente (mantendrá tu misma red Wi-Fi y tu mismo usuario `pi@pi5.local`).

### Consideraciones sobre el Autoarranque al Migrar
* Si tenías el servicio activado en la Pi anterior, la nueva Pi intentará arrancar la IA de inmediato.
* Si habías desactivado el servicio (`sudo systemctl disable bee-counter.service`) antes de apagar la placa anterior, la nueva Pi recordará esa configuración y **no iniciará la IA automáticamente**. Para volver a probar manualmente en la nueva placa (para ver tus FPS), simplemente entra a la carpeta, activa el entorno y corre el script:

```bash
cd ~/tetragonisca-vision-edgeai
source ~/edgeai_env/bin/activate
python main.py --video 0040-1.mp4 --no-output --num-threads 4
```
*(Si la nueva placa es más potente, puedes reducir los hilos o quitar el `--skip-frames` para máxima calidad).*
