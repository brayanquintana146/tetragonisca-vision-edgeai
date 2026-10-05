import argparse
import csv
import os
import sys
import threading
import time
import cv2
import numpy as np

# Importación de Google LiteRT (ai-edge-litert) con respaldos dinámicos
try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        import tflite_runtime.interpreter as tflite
    except ImportError:
        # Windows/PC: LiteRT y tflite_runtime no tienen ruedas para Windows; se usa TensorFlow
        # pyrefly: ignore [missing-import]
        import tensorflow as _tf
        tflite = _tf.lite

from src.counter import BeeCounter, BeeCounterV2, BeeCounterHybrid
from src.tracker import EuTrack, BeeTracker
from src.detection import cluster_centroids
from src.dashboard import Dashboard


class LatestFrameReader:
    """
    Lee la cámara en un hilo aparte y guarda solo el frame más reciente.

    Sin esto, cv2.VideoCapture entrega frames viejos del buffer cuando la
    inferencia es más lenta que la cámara: el tracker recibe imágenes con
    retraso y huecos de tiempo irregulares.
    """

    def __init__(self, cap):
        self.cap = cap
        self.lock = threading.Lock()
        self.frame, self.t, self.seq = None, None, 0
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            ok, f = self.cap.read()
            t = time.monotonic()
            if not ok:
                self.running = False
                break
            with self.lock:
                self.frame, self.t, self.seq = f, t, self.seq + 1

    def read(self, last_seq):
        """Espera un frame más nuevo que last_seq. Devuelve (ok, frame, t, seq)."""
        while self.running or self.seq > last_seq:
            with self.lock:
                if self.seq > last_seq:
                    return True, self.frame, self.t, self.seq
            time.sleep(0.001)
        return False, None, None, last_seq

    def stop(self):
        self.running = False
        self.thread.join(timeout=1.0)


class FOMODetector:
    """
    Detector de centroides basado en el modelo FOMO (.lite / .tflite) exportado desde Edge Impulse.
    """

    def __init__(self, model_path="models/fomo_tetragonisca_int8.lite", threshold=0.6, num_threads=1,
                 crop_center=None):
        self.interpreter = tflite.Interpreter(
            model_path=model_path,
            num_threads=num_threads,   # multi-core en Pi 5: usar 4
        )
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Obtener resolución de entrada requerida por FOMO (ej. 96x96 o 160x160)
        self.input_height = self.input_details[0]['shape'][1]
        self.input_width = self.input_details[0]['shape'][2]
        self.threshold = threshold
        # Si se define, se recorta un cuadrado del lado corto del frame centrado aquí (x, y),
        # igual que "Fit shortest axis" de Edge Impulse, en vez de aplastar el frame completo
        self.crop_center = crop_center

    def crop_box(self, frame_w, frame_h):
        """Región (x0, y0, ancho, alto) del frame que entra al modelo."""
        if self.crop_center is None:
            return 0, 0, frame_w, frame_h
        side = min(frame_w, frame_h)
        x0 = int(np.clip(self.crop_center[0] - side // 2, 0, frame_w - side))
        y0 = int(np.clip(self.crop_center[1] - side // 2, 0, frame_h - side))
        return x0, y0, side, side

    def detect(self, frame):
        """Centroides agrupados con el método v1 (radio fijo de 60 px)."""
        return self._cluster_centroids(self.detect_raw(frame))

    def detect_raw(self, frame):
        """Celdas de FOMO sobre el umbral: lista de (cx, cy, prob) en px del frame."""
        frame_h, frame_w = frame.shape[:2]

        # 1. Preprocesamiento: recortar (opcional), redimensionar y convertir BGR a RGB
        x0, y0, crop_w, crop_h = self.crop_box(frame_w, frame_h)
        region = frame[y0:y0 + crop_h, x0:x0 + crop_w]
        resized = cv2.resize(region, (self.input_width, self.input_height))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # 2. Normalización y cuantización a INT8 [-128, 127]
        input_data = (np.expand_dims(rgb, axis=0).astype(np.int32) - 128).astype(np.int8)

        # 3. Ejecutar inferencia con LiteRT
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # 4. Obtener tensor de salida (grilla de mapa de calor de centroides)
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])

        raw_centroids = []
        # Formato de salida habitual de FOMO: [1, grid_h, grid_w, num_classes]
        if len(output_data.shape) == 4:
            grid_h, grid_w = output_data.shape[1], output_data.shape[2]
            num_classes = output_data.shape[3]

            for y in range(grid_h):
                for x in range(grid_w):
                    # Si hay más de 1 clase, la clase 1 es 'Abeja'
                    prob_int8 = output_data[0, y, x, 1] if num_classes > 1 else output_data[0, y, x, 0]
                    prob = (float(prob_int8) + 128) / 256.0
                    if prob > self.threshold:
                        # Convertir coordenada de grilla a píxel real del video original
                        cx = x0 + int((x + 0.5) * (crop_w / grid_w))
                        cy = y0 + int((y + 0.5) * (crop_h / grid_h))
                        raw_centroids.append((cx, cy, prob))

        return raw_centroids

    @staticmethod
    def _cluster_centroids(raw_centroids, merge_radius=60):
        """
        Agrupa centroides que están a menos de merge_radius píxeles entre sí.
        Devuelve el centroide promedio ponderado por confianza de cada grupo.
        Esto evita que una sola abeja genere 2-3 detecciones en celdas adyacentes.
        """
        if not raw_centroids:
            return []

        # Ordenar por confianza descendente (los más fuertes anclan los clusters)
        raw_centroids.sort(key=lambda c: c[2], reverse=True)

        merged = []
        used = [False] * len(raw_centroids)

        for i in range(len(raw_centroids)):
            if used[i]:
                continue

            cx_sum = raw_centroids[i][0] * raw_centroids[i][2]
            cy_sum = raw_centroids[i][1] * raw_centroids[i][2]
            weight_sum = raw_centroids[i][2]
            used[i] = True

            # Absorber todos los vecinos cercanos
            for j in range(i + 1, len(raw_centroids)):
                if used[j]:
                    continue
                dx = raw_centroids[i][0] - raw_centroids[j][0]
                dy = raw_centroids[i][1] - raw_centroids[j][1]
                if (dx * dx + dy * dy) <= merge_radius * merge_radius:
                    cx_sum += raw_centroids[j][0] * raw_centroids[j][2]
                    cy_sum += raw_centroids[j][1] * raw_centroids[j][2]
                    weight_sum += raw_centroids[j][2]
                    used[j] = True

            # Centroide promedio ponderado del cluster
            merged.append((int(cx_sum / weight_sum), int(cy_sum / weight_sum)))

        return merged


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline principal con LiteRT, EuTrack y BeeCounter"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Ruta al video (.mp4)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/fomo_tetragonisca_int8.lite",
        help="Ruta al modelo .lite / .tflite",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output_result.mp4",
        help="Ruta para guardar el video procesado",
    )
    parser.add_argument("--roi-x", type=int, default=900, help="Centro X de la piquera")
    parser.add_argument("--roi-y", type=int, default=640, help="Centro Y de la piquera")
    parser.add_argument("--roi-r", type=int, default=200, help="Radio de la piquera en px")
    parser.add_argument("--crop-roi", action="store_true",
                        help="Recortar un cuadrado (lado corto del frame) centrado en la ROI antes del modelo, "
                             "como 'Fit shortest axis' de Edge Impulse, en vez de aplastar el frame completo")
    parser.add_argument("--tracker", choices=["v2", "v1"], default="v2",
                        help="v2: Kalman + gating, independiente de resolución y FPS (defecto). v1: EuTrack original")
    parser.add_argument("--threshold", type=float, default=0.55, help="Umbral de confianza FOMO (v2: para crear abejas nuevas)")
    parser.add_argument("--assoc-threshold", type=float, default=0.35,
                        help="v2: umbral menor para seguir abejas ya rastreadas (detecciones borrosas)")
    parser.add_argument("--max-lost", type=float, default=0.6, help="v2: segundos sin detección antes de cerrar un track")
    parser.add_argument("--max-gate", type=float, default=1.2,
                        help="v2: distancia máxima (en radios de la ROI) para unir una detección a un track. "
                             "Menor = los tracks saltan menos entre abejas vecinas")
    parser.add_argument("--max-gate-tentative", type=float, default=None,
                        help="v2: --max-gate para tracks nuevos sin confirmar (defecto: igual a --max-gate). "
                             "Más grande = enlaza abejas en vuelo rápido")
    parser.add_argument("--counter", choices=["v2", "hibrido"], default="v2",
                        help="v2: una entrada/salida por track. hibrido: cuenta cada salida que cruza el borde "
                             "(recupera las que un track largo se tragaba) y las entradas como v2")
    parser.add_argument("--cancel-s", type=float, default=0.5,
                        help="hibrido: si una abeja cruza hacia fuera y vuelve antes de estos segundos, no cuenta")
    parser.add_argument("--proj-min-speed", type=float, default=1.5,
                        help="hibrido: velocidad mínima (radios/s) para proyectar fuera de la ROI un track que se cierra. "
                             "Mayor = menos salidas falsas y menos salidas detectadas")
    parser.add_argument("--track-scale", type=float, default=None,
                        help="v2: px que usa el tracker como unidad de distancia (defecto: --roi-r). Permite achicar "
                             "el círculo de conteo sin que el tracker parta una abeja en dos (p. ej. --roi-r 100 --track-scale 220)")
    parser.add_argument("--flash-exits", action="store_true",
                        help="hibrido: contar también las salidas que FOMO solo ve 1-3 frames (despegues borrosos) "
                             "y no proyectar fuera de la ROI los tracks que se cierran")
    parser.add_argument("--accel-std", type=float, default=40.0,
                        help="v2: aceleración típica de una abeja (radios/s²). Mayor = sigue mejor los despegues bruscos")
    parser.add_argument("--max-disappeared", type=int, default=20, help="v1: frames tolerados sin deteccion antes de perder ID")
    parser.add_argument("--max-distance", type=int, default=250, help="v1: distancia euclidiana maxima (px) para mantener ID")
    parser.add_argument("--cam-width", type=int, default=0, help="Ancho pedido a la cámara (0 = por defecto del driver)")
    parser.add_argument("--cam-height", type=int, default=0, help="Alto pedido a la cámara")
    parser.add_argument("--cam-fps", type=int, default=0, help="FPS pedidos a la cámara")
    parser.add_argument("--events", type=str, default=None, help="v2: CSV con cada evento IN/OUT (tiempo, id, posición)")
    parser.add_argument("--show", action="store_true", help="Mostrar ventana de OpenCV (solo PC)")
    parser.add_argument("--num-threads", type=int, default=1, help="Hilos para inferencia TFLite (4 en Pi 5)")
    parser.add_argument("--skip-frames", type=int, default=1, help="Procesar 1 de cada N frames (acelera en hardware lento)")
    parser.add_argument("--no-output", action="store_true", help="No guardar video de salida (ahorra CPU/disco en Pi)")
    parser.add_argument("--log", type=str, default=None, help="Ruta CSV para guardar log de conteo por frame")
    parser.add_argument("--dashboard", action="store_true", help="Lanzar dashboard web en :5000")
    parser.add_argument("--snapshot-every", type=int, default=0, help="Guardar frame anotado cada N frames (0=desactivado, util para verificar tracking sin --show)")
    parser.add_argument("--snapshot-dir", type=str, default="snapshots", help="Directorio donde guardar los snapshots")

    args = parser.parse_args()

    use_v2 = args.tracker == "v2"
    track_scale = args.track_scale or args.roi_r
    if args.flash_exits and not (use_v2 and args.counter == "hibrido"):
        parser.error("--flash-exits necesita --tracker v2 --counter hibrido")

    # Inicializar detector FOMO con LiteRT (v2 usa un umbral bajo y filtra después)
    det_threshold = min(args.threshold, args.assoc_threshold) if use_v2 else args.threshold
    detector = FOMODetector(model_path=args.model, threshold=det_threshold, num_threads=args.num_threads,
                            crop_center=(args.roi_x, args.roi_y) if args.crop_roi else None)

    is_camera = args.video.isdigit() or args.video.startswith("/dev/video")
    video_source = int(args.video) if args.video.isdigit() else args.video
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir el video '{args.video}'.")
        sys.exit(1)

    if is_camera:
        # MJPG permite 30 fps a resoluciones altas por USB en webcams Logitech
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        if args.cam_width and args.cam_height:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.cam_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.cam_height)
        if args.cam_fps:
            cap.set(cv2.CAP_PROP_FPS, args.cam_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # La ROI tiene que caber completa en el frame; si no, el conteo falla en silencio
    if (args.roi_x - args.roi_r < 0 or args.roi_y - args.roi_r < 0
            or args.roi_x + args.roi_r > width or args.roi_y + args.roi_r > height):
        print(f"[AVISO] La ROI (centro=({args.roi_x},{args.roi_y}), r={args.roi_r}) se sale del "
              f"frame {width}x{height}. Revisa --roi-x/--roi-y/--roi-r para esta resolución.")

    if is_camera and args.skip_frames > 1:
        print("[AVISO] --skip-frames con cámara en vivo reduce los FPS efectivos del tracker. "
              "Con cámara se procesa siempre el frame más reciente; se ignora --skip-frames.")
        args.skip_frames = 1

    if not args.no_output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    else:
        out = None

    if use_v2:
        # Todas las distancias del tracker v2 se miden en radios de la ROI
        tracker = BeeTracker(scale=track_scale, max_lost_s=args.max_lost, birth_min_prob=args.threshold,
                             max_gate=args.max_gate, accel_std=args.accel_std,
                             max_gate_tentative=args.max_gate_tentative)
        if args.counter == "hibrido":
            counter = BeeCounterHybrid(roi_center=(args.roi_x, args.roi_y), roi_radius=args.roi_r,
                                       cancel_s=args.cancel_s, proj_min_speed=args.proj_min_speed,
                                       flash_exits=args.flash_exits, track_scale=track_scale)
        else:
            counter = BeeCounterV2(roi_center=(args.roi_x, args.roi_y), roi_radius=args.roi_r)
    else:
        tracker = EuTrack(max_disappeared=args.max_disappeared, max_distance=args.max_distance)
        counter = BeeCounter(roi_center=(args.roi_x, args.roi_y), roi_radius=args.roi_r)

    events_file = None
    events_writer = None
    n_events_written = 0
    if args.events and use_v2:
        events_file = open(args.events, "w", newline="", encoding="utf-8")
        events_writer = csv.writer(events_file)
        events_writer.writerow(["t_s", "evento", "id", "x", "y"])

    # Dashboard web (opcional)
    dashboard = None
    if args.dashboard:
        dashboard = Dashboard()
        dashboard.start()

    # Log CSV (opcional)
    csv_file = None
    csv_writer = None
    if args.log:
        csv_file = open(args.log, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['frame', 'timestamp', 'in', 'out', 'total', 'fps_proc'])

    # Directorio de snapshots (opcional)
    if args.snapshot_every > 0:
        os.makedirs(args.snapshot_dir, exist_ok=True)

    print("=" * 60)
    print("TETRAGONISCA VISION EDGEAI - INFERENCIA LITERT + ROI COUNTER")
    print("=" * 60)
    print(f"Modelo TFLite : {args.model}")
    print(f"Video Entrada : {args.video} ({width}x{height} a {fps} FPS)")
    print(f"Piquera ROI   : Centro=({args.roi_x}, {args.roi_y}), Radio={args.roi_r} px")
    print(f"Tracker       : {'v2 (Kalman + gating, tiempo real)' if use_v2 else 'v1 (EuTrack)'}")
    cx0, cy0, cw, ch = detector.crop_box(width, height)
    print(f"Entrada modelo: {'recorte ' if args.crop_roi else 'frame completo '}"
          f"x={cx0}..{cx0 + cw}, y={cy0}..{cy0 + ch} -> {detector.input_width}x{detector.input_height}")
    print("-" * 60)
    if args.num_threads > 1:
        print(f"Hilos TFLite  : {args.num_threads} (multi-core)")
    if args.skip_frames > 1:
        print(f"Skip frames   : 1 de cada {args.skip_frames}")
    if args.no_output:
        print("Output video  : DESACTIVADO")
    if args.dashboard:
        print("Dashboard web : http://0.0.0.0:5000")
    print("-" * 60)

    frame_idx = 0
    processed_frames = 0
    total_processing_time = 0.0
    t_last = time.perf_counter()
    global_start_time = time.time()

    if args.show:
        win_name = "Tetragonisca Vision - Inferencia y Conteo"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, min(width, 1280), min(height, 720))

    reader = LatestFrameReader(cap) if is_camera else None
    last_seq = 0
    t_start_cam = None
    counts = {"in": 0, "out": 0}

    while True:
        if reader is not None:
            ret, frame, t_cap, last_seq = reader.read(last_seq)
            if not ret:
                break
            if t_start_cam is None:
                t_start_cam = t_cap
            t_frame = t_cap - t_start_cam          # tiempo real de captura
        else:
            ret, frame = cap.read()
            if not ret:
                break
            t_frame = frame_idx / fps              # tiempo del video

        frame_idx += 1

        # Saltar frames para reducir carga de inferencia en hardware lento
        if frame_idx % args.skip_frames != 0:
            if out is not None:
                out.write(frame)  # escribir frame sin anotar al output
            continue

        t0 = time.perf_counter()
        processed_frames += 1

        if use_v2:
            # 1. Inferencia FOMO + agrupación relativa al tamaño de la ROI
            centroids = cluster_centroids(detector.detect_raw(frame), merge_radius=0.25 * track_scale)
            # 2. Tracking con el tiempo real del frame
            active, finished = tracker.update(centroids, t_frame)
            # 3. Conteo origen-destino
            if args.flash_exits:
                counts = counter.update(active, finished, detections=centroids, t=t_frame)
            else:
                counts = counter.update(active, finished)
            objects = {tr.id: tr.pos for tr in active if tr.misses <= 2}
            if events_writer is not None:
                for ev in counter.events[n_events_written:]:
                    events_writer.writerow([round(ev[0], 3), ev[1], ev[2], int(ev[3]), int(ev[4])])
                n_events_written = len(counter.events)
        else:
            # 1. Inferencia real con FOMO
            centroids = detector.detect(frame)
            # 2. Tracking de centroides (EuTrack)
            objects, deregistered = tracker.update(centroids)
            # 3. Conteo en la ROI de la piquera (BeeCounter)
            counts = counter.update(objects, tracker.trajectories, deregistered=deregistered)

        total_ids = tracker.confirmed_total if use_v2 else tracker.next_object_id

        # Calcular si necesitamos renderizar el frame
        # (solo cuando hay que mostrarlo, guardarlo en video o hacer snapshot)
        need_snapshot = args.snapshot_every > 0 and frame_idx % args.snapshot_every == 0
        need_render = out is not None or args.show or need_snapshot

        if need_render:
            # 4. Renderizado visual (Piquera, IDs, Trayectorias y HUD)
            # Círculo virtual de la piquera
            cv2.circle(frame, (args.roi_x, args.roi_y), args.roi_r, (0, 255, 255), 2)
            cv2.circle(frame, (args.roi_x, args.roi_y), 4, (0, 255, 255), -1)
            if args.crop_roi:
                # Región que ve el modelo; fuera de ella no hay detecciones
                cv2.rectangle(frame, (cx0, cy0), (cx0 + cw - 1, cy0 + ch - 1), (255, 128, 0), 1)

            # Dibujar centroides, IDs y trayectorias (solo objetos activamente detectados)
            trails = tracker.trajectories
            for object_id, centroid in objects.items():
                # No dibujar objetos "fantasma" que ya no están siendo detectados
                if not use_v2 and tracker.disappeared.get(object_id, 0) > 2:
                    continue

                cx, cy = int(centroid[0]), int(centroid[1])

                # Centroide actual (punto rojo sólido)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(
                    frame,
                    f"ID {object_id}",
                    (cx + 8, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1,
                )

                # Trayectoria como puntos que se desvanecen
                if object_id in trails:
                    trail = trails[object_id]
                    n = len(trail)
                    for i, pt in enumerate(trail):
                        # Opacidad: los puntos más recientes son más visibles
                        alpha = (i + 1) / n
                        color = (
                            int(255 * alpha),   # B: azul claro al final
                            int(180 * alpha),   # G
                            int(50 * alpha),    # R
                        )
                        radius = max(1, int(3 * alpha))
                        cv2.circle(frame, (int(pt[0]), int(pt[1])), radius, color, -1)

            # Tablero de Estadísticas (HUD Transparente)
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (300, 105), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            cv2.putText(
                frame,
                "Tetragonisca Vision EdgeAI",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
            cv2.putText(
                frame,
                f"Entradas (IN) : {counts['in']}",
                (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Salidas  (OUT): {counts['out']}",
                (20, 88),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

            if out is not None:
                out.write(frame)

            # Guardar snapshot periódico para verificar tracking sin pantalla
            if need_snapshot:
                snap_path = os.path.join(args.snapshot_dir, f"snap_{frame_idx:06d}.jpg")
                cv2.imwrite(snap_path, frame)

        # Calcular FPS sobre el tiempo total del frame (inferencia + render si aplica)
        t_now = time.perf_counter()
        proc_time = t_now - t0
        total_processing_time += proc_time
        fps_proc = 1.0 / max(proc_time, 1e-6)

        # Actualizar log CSV
        if csv_writer is not None:
            csv_writer.writerow([
                frame_idx,
                round(t_now, 3),
                counts['in'], counts['out'],
                total_ids,
                round(fps_proc, 2),
            ])

        # Actualizar dashboard web
        if dashboard is not None:
            dashboard.update(
                in_count=counts['in'],
                out_count=counts['out'],
                total=total_ids,
                frame=frame_idx,
                fps_proc=fps_proc,
            )

        # Imprimir progreso en consola (para saber que no está congelado)
        if frame_idx % 30 == 0:
            elapsed = time.time() - global_start_time
            m, s = divmod(int(elapsed), 60)
            h, m = divmod(m, 60)
            time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            print(f"[{time_str}] Procesando frame {frame_idx:05d} | FPS: {fps_proc:.1f} | IN: {counts['in']} | OUT: {counts['out']}")

        if args.show:
            cv2.imshow("Tetragonisca Vision - Inferencia y Conteo", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if reader is not None:
        reader.stop()

    # Cerrar los tracks abiertos al terminar (conteo de las abejas del último instante)
    if use_v2:
        counts = counter.update([], tracker.flush(), final=True) if args.flash_exits \
            else counter.update([], tracker.flush())
        total_ids = tracker.confirmed_total
        if events_writer is not None:
            for ev in counter.events[n_events_written:]:
                events_writer.writerow([round(ev[0], 3), ev[1], ev[2], int(ev[3]), int(ev[4])])
    else:
        total_ids = tracker.next_object_id
    if events_file is not None:
        events_file.close()

    cap.release()
    if out is not None:
        out.release()
    if csv_file is not None:
        csv_file.close()
    if args.show:
        cv2.destroyAllWindows()

    total_elapsed = time.time() - global_start_time
    m, s = divmod(int(total_elapsed), 60)
    h, m = divmod(m, 60)
    total_time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    avg_fps = (processed_frames / total_processing_time) if total_processing_time > 0 else 0.0

    print("\n" + "=" * 60)
    print(" " * 17 + "RESUMEN DE PROCESAMIENTO")
    print("=" * 60)
    print(f" Tiempo Total de Ejecución : {total_time_str}")
    print(f" Velocidad Promedio (IA)   : {avg_fps:.1f} FPS")
    print("-" * 60)
    print(f" Total Cuadros (Video)     : {frame_idx}")
    print(f" Cuadros Procesados (IA)   : {processed_frames}")
    print("-" * 60)
    print(f" Identidades Únicas        : {total_ids}")
    print(f" Entradas (IN)             : {counts['in']}")
    print(f" Salidas (OUT)             : {counts['out']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
