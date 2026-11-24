# Despliegue en Raspberry Pi 5

Pasos para instalar y correr el contador en una Raspberry Pi 5 sin escritorio. Los comandos de conteo y la configuración recomendada están en el [README](README.md).

## 1. Sistema operativo

Con Raspberry Pi Imager:

1. Dispositivo: **Raspberry Pi 5**.
2. Sistema: **Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)**. Sin escritorio queda más memoria para la inferencia.
3. Almacenamiento: la tarjeta MicroSD (se borra por completo).
4. Personalización:
   - Nombre del equipo: `pi5`.
   - Usuario `pi` con una contraseña propia.
   - Red Wi-Fi de 2.4 GHz (por ejemplo, la zona de cobertura del PC). El nombre y la contraseña de la red no se guardan en el repositorio.
   - Zona horaria y teclado.
   - Servicios: **SSH** con contraseña.
5. Escribir y esperar la verificación.

## 2. Primer arranque

Con la MicroSD en la Pi y la Pi encendida, a los pocos minutos se conecta a la red. Desde el PC:

```bash
ssh pi@pi5.local
```

Si `.local` no resuelve, se usa la IP de la Pi (`ssh pi@<ip>`). La primera vez se acepta la clave del equipo con `yes`.

## 3. Entorno de Python

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-venv -y
python3 -m venv ~/edgeai_env
source ~/edgeai_env/bin/activate   # en cada sesión SSH
```

## 4. Código y dependencias

El repositorio se clona en la Pi, o se copian desde el PC solo los archivos necesarios:

```powershell
# En el PC, desde la raíz del proyecto
ssh pi@pi5.local "mkdir -p ~/tetragonisca-vision-edgeai"
scp main.py requirements-pi.txt pi@pi5.local:~/tetragonisca-vision-edgeai/
scp -r src models examples pi@pi5.local:~/tetragonisca-vision-edgeai/
```

```bash
# En la Pi
cd ~/tetragonisca-vision-edgeai
pip install -r requirements-pi.txt
```

Los modelos v3 a v8 están en `models/`.

> **Sin DNS** (`Temporary failure in name resolution`): la zona de cobertura de Windows a veces no entrega el DNS. Solución rápida:
> ```bash
> echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
> ```

## 5. Cámara y prueba manual

**Energía:** con cámara e inferencia la Pi 5 consume 15–25 W. Con el USB de una laptop se reinicia; se necesita una fuente de pared de al menos 5 V 3 A. La cámara se conecta con la Pi apagada: una webcam USB a un puerto azul (USB 3.0), o la cámara oficial al conector `CAM/DISP`.

```bash
ssh pi@pi5.local
source ~/edgeai_env/bin/activate
cd ~/tetragonisca-vision-edgeai

# Video grabado
python main.py --video examples/videos/0040-1.mp4 --no-output --num-threads 4

# Cámara en vivo a 640x480 y 30 fps. La ROI va en píxeles de esa resolución
# y debe rodear la piquera tal como se ve en la imagen. Si se sale del cuadro, el programa avisa.
python main.py --video 0 --cam-width 640 --cam-height 480 --cam-fps 30 \
  --roi-x 320 --roi-y 240 --roi-r 100 --num-threads 4 --snapshot-every 150
```

- **Calibrar la ROI:** con `--snapshot-every 150` se guardan imágenes en `snapshots/`. El círculo amarillo debe cubrir la piquera con un margen de un cuerpo de abeja. El tracker mide sus distancias en radios de la ROI, así que un radio mal puesto cambia el conteo.
- **Webcam (Logitech C930e u otra UVC):** con poca luz alarga la exposición, baja a ~15 fps y las abejas en vuelo salen borrosas. Conviene fijar la exposición y apagar el autofoco. Los nombres de los controles dependen del kernel (`v4l2-ctl -d /dev/video0 --list-ctrls`); en Raspberry Pi OS suelen ser:
  ```bash
  sudo apt install v4l-utils
  v4l2-ctl -d /dev/video0 -c auto_exposure=1 -c exposure_time_absolute=100 -c exposure_dynamic_framerate=0
  v4l2-ctl -d /dev/video0 -c focus_automatic_continuous=0 -c focus_absolute=0
  ```
  `exposure_time_absolute` va en unidades de 100 µs (100 = 10 ms).
- **Monitoreo**, en otra sesión SSH: `htop` (CPU y RAM) y `watch -n 1 vcgencmd measure_temp` (temperatura; conviene que no pase de 80 °C).
- **Detener:** `Ctrl+C`.
- **Video anotado:** sin `--no-output` se genera `output_result.mp4`. La Pi no tiene escritorio (`--show` no funciona), así que se copia al PC:
  ```powershell
  scp pi@pi5.local:~/tetragonisca-vision-edgeai/output_result.mp4 .
  ```

**Apagado:** siempre con `sudo shutdown -h now`, y desenchufar cuando la luz verde deje de parpadear. Cortar la energía de golpe puede dañar la MicroSD.

## 6. Demostración con videos grabados

El conteo se demuestra con videos grabados, no con la cámara filmando una pantalla (el parpadeo, los reflejos y el tamaño cambian los resultados). Con la configuración recomendada, y el dashboard en `http://pi5.local:5000`:

```bash
python main.py --video examples/videos/0040-1.mp4 --model models/v5_fomo_borrosas_480_int8.lite --roi-x 900 --roi-y 600 --roi-r 220 --crop-roi --counter hibrido --max-gate 0.9 --max-gate-tentative 1.2 --accel-std 260 --threshold 0.7 --max-lost 0.3 --proj-min-speed 3.0 --flash-exits --static-s 2 --core 0.5 --cancel-s 1.0 --num-threads 4 --dashboard --output video_demo.mp4 --events eventos_demo.csv
```

Con un archivo de video se procesan todos los cuadros, así que el conteo no depende de la velocidad de la Pi. La cámara en vivo puede mostrarse unos segundos (comando del paso 5 con `--snapshot-every 30`) para ver que captura y detecta; esos conteos no se presentan.

## 7. Arranque automático (systemd)

`/etc/systemd/system/bee-counter.service`:

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

[Install]
WantedBy=multi-user.target
```

Con `--dashboard`, el conteo en tiempo real se ve desde la misma red en `http://pi5.local:5000`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bee-counter.service   # activar e iniciar
sudo journalctl -u bee-counter.service -f         # ver registros
sudo systemctl stop bee-counter.service           # detener
sudo systemctl disable bee-counter.service        # no arrancar al encender
```

## 8. Opciones útiles

- `--log conteos.csv`: número de abejas por cuadro.
- `--events eventos.csv` (tracker v2): una fila por entrada o salida con tiempo, ID y posición, para validar contra el video.
- `--skip-frames 3`: con archivos de video procesa 1 de cada 3 cuadros. Con cámara en vivo se ignora: la cámara se lee en un hilo aparte y siempre se procesa el cuadro más reciente. Para contar bien las salidas conviene mantener al menos ~15 fps efectivos (línea `FPS:` de la consola).
- `taskset -c 0,1,2 python main.py ... --num-threads 3`: limita la inferencia a 3 núcleos y deja uno libre (menos temperatura, espacio para los sensores).

## 9. Cambio de placa

El sistema, las librerías y el servicio viven en la MicroSD. Para pasar a otra placa basta apagarla con `sudo shutdown -h now`, mover la tarjeta y encender: arranca con la misma red, el mismo usuario y el mismo estado del servicio (activado o no).
