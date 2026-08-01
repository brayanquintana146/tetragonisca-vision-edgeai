import argparse
import sys
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
        # pyrefly: ignore [missing-import]
        import tensorflow.lite as tflite

from src.counter import BeeCounter
from src.tracker import EuTrack


class FOMODetector:
    """
    Detector de centroides basado en el modelo FOMO (.lite / .tflite) exportado desde Edge Impulse.
    """

    def __init__(self, model_path="models/fomo_tetragonisca_int8.lite", threshold=0.6):
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Obtener resolución de entrada requerida por FOMO (ej. 96x96 o 160x160)
        self.input_height = self.input_details[0]['shape'][1]
        self.input_width = self.input_details[0]['shape'][2]
        self.threshold = threshold

    def detect(self, frame):
        frame_h, frame_w = frame.shape[:2]

        # 1. Preprocesamiento: Redimensionar y convertir BGR a RGB
        resized = cv2.resize(frame, (self.input_width, self.input_height))
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
                        cx = int((x + 0.5) * (frame_w / grid_w))
                        cy = int((y + 0.5) * (frame_h / grid_h))
                        raw_centroids.append((cx, cy, prob))

        # 5. Agrupar detecciones cercanas (NMS por distancia) para evitar
        #    que una misma abeja genere múltiples centroides en celdas vecinas
        return self._cluster_centroids(raw_centroids)

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
    parser.add_argument("--threshold", type=float, default=0.55, help="Umbral de confianza FOMO")
    parser.add_argument("--max-disappeared", type=int, default=20, help="Frames tolerados sin deteccion antes de perder ID")
    parser.add_argument("--max-distance", type=int, default=250, help="Distancia euclidiana maxima (px) para mantener ID")
    parser.add_argument("--show", action="store_true", help="Mostrar ventana de OpenCV")

    args = parser.parse_args()

    # Inicializar detector FOMO con LiteRT
    detector = FOMODetector(model_path=args.model, threshold=args.threshold)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir el video '{args.video}'.")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))

    tracker = EuTrack(max_disappeared=args.max_disappeared, max_distance=args.max_distance)
    counter = BeeCounter(roi_center=(args.roi_x, args.roi_y), roi_radius=args.roi_r)

    print("=" * 60)
    print("TETRAGONISCA VISION EDGEAI - INFERENCIA LITERT + ROI COUNTER")
    print("=" * 60)
    print(f"Modelo TFLite : {args.model}")
    print(f"Video Entrada : {args.video}")
    print(f"Piquera ROI   : Centro=({args.roi_x}, {args.roi_y}), Radio={args.roi_r} px")
    print("-" * 60)

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # 1. Inferencia real con FOMO
        centroids = detector.detect(frame)

        # 2. Tracking de centroides (EuTrack)
        objects, deregistered = tracker.update(centroids)

        # 3. Conteo en la ROI de la piquera (BeeCounter)
        counts = counter.update(objects, tracker.trajectories, deregistered=deregistered)

        # 4. Renderizado visual (Piquera, IDs, Trayectorias y HUD)
        # Círculo virtual de la piquera
        cv2.circle(frame, (args.roi_x, args.roi_y), args.roi_r, (0, 255, 255), 2)
        cv2.circle(frame, (args.roi_x, args.roi_y), 4, (0, 255, 255), -1)

        # Dibujar centroides, IDs y trayectorias (solo objetos activamente detectados)
        for object_id, centroid in objects.items():
            # No dibujar objetos "fantasma" que ya no están siendo detectados
            if tracker.disappeared.get(object_id, 0) > 2:
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
            if object_id in tracker.trajectories:
                trail = tracker.trajectories[object_id]
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
        cv2.rectangle(overlay, (10, 10), (300, 135), (0, 0, 0), -1)
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
        cv2.putText(
            frame,
            f"Total Abejas  : {tracker.next_object_id}",
            (20, 116),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2,
        )

        out.write(frame)

        if args.show:
            cv2.imshow("Tetragonisca Vision - Inferencia y Conteo", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    out.release()
    if args.show:
        cv2.destroyAllWindows()

    print("\n" + "=" * 60)
    print("PROCESAMIENTO COMPLETADO")
    print(f"Frames procesados : {frame_idx}")
    print(f"Total Abejas      : {tracker.next_object_id}")
    print(f"Entradas (IN)     : {counts['in']}")
    print(f"Salidas  (OUT)    : {counts['out']}")
    print("=" * 60)


if __name__ == "__main__":
    main()