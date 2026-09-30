"""
Extrae frames de abejas DESPEGANDO para reentrenar FOMO.

Usa la anotación manual (tools/anotar_eventos.py) para saber cuándo y dónde
sale cada abeja, y guarda algunos frames alrededor de cada salida. Solo toma
salidas ANTES de --split segundos: la otra parte del video queda reservada
para evaluar (bench/compare_events.py ... --start SPLIT) sin fuga de datos.

Salida (--out, por defecto data/despegues/):
  train/        imágenes .png + etiquetas YOLO .txt + classes.txt ("Abeja")
                -> carpeta lista para edge-impulse-uploader --dataset-format yolo-txt
  referencia/   mismas imágenes con la posición anotada de la salida (círculo
                magenta) y las cajas pre-etiquetadas (verde). NO se suben:
                sirven para saber qué abeja buscar al etiquetar.

Pre-etiquetado (--prelabel, activo por defecto): las abejas que el modelo
actual YA detecta se guardan como cajas, para que solo tengas que corregir y
agregar las que faltan (sobre todo la abeja en vuelo). FOMO solo da centroides,
así que las cajas tienen un tamaño fijo (--box-w x --box-h px, la mediana del
dataset 004); ajústalas si hace falta.

Uso:
  python scripts/04_extraer_despegues.py --gt data/gt_0040-1.csv ^
      --video examples/videos/0040-1.mp4 --split 30
"""
import argparse
import csv
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser(description="Extrae frames de despegues para reentrenar FOMO")
    ap.add_argument("--gt", required=True, help="CSV de tools/anotar_eventos.py")
    ap.add_argument("--video", required=True)
    ap.add_argument("--split", type=float, default=30.0,
                    help="solo usa salidas antes de este segundo (el resto se reserva para evaluar)")
    ap.add_argument("--offsets", default="-6,-3,0,3,6",
                    help="frames relativos al evento a extraer (60 fps: 3 frames = 0.05 s)")
    ap.add_argument("--out", default="data/despegues")
    ap.add_argument("--prefix", default=None, help="prefijo de los archivos (por defecto, nombre del video)")
    ap.add_argument("--no-prelabel", action="store_true", help="no pre-etiquetar con el modelo actual")
    ap.add_argument("--model", default="models/fomo_tetragonisca_int8.lite")
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--box-w", type=int, default=59, help="ancho (px) de las cajas pre-etiquetadas")
    ap.add_argument("--box-h", type=int, default=80, help="alto (px) de las cajas pre-etiquetadas")
    ap.add_argument("--merge-px", type=int, default=55, help="radio para agrupar celdas de FOMO")
    a = ap.parse_args()

    offsets = [int(v) for v in a.offsets.split(",")]
    prefix = a.prefix or os.path.splitext(os.path.basename(a.video))[0]

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"No se pudo abrir {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    split_frame = int(a.split * fps)

    # Salidas anotadas antes del corte
    outs = []
    with open(a.gt, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["evento"].strip().lower() == "out" and float(r["t_s"]) < a.split:
                fr = int(r["frame"]) if r.get("frame") else int(round(float(r["t_s"]) * fps))
                outs.append((fr, int(r["x"]), int(r["y"])))
    if not outs:
        raise SystemExit("No hay salidas anotadas antes de --split")

    # Frames a extraer (sin pasar el corte) y qué salidas caen en cada uno
    wanted = {}
    for fr, x, y in outs:
        for o in offsets:
            k = fr + o
            if 0 <= k < min(split_frame, n_frames):
                wanted.setdefault(k, []).append((x, y))

    detector = None
    if not a.no_prelabel:
        from main import FOMODetector
        from src.detection import cluster_centroids
        detector = FOMODetector(model_path=a.model, threshold=a.threshold, num_threads=4)

    d_train = os.path.join(a.out, "train")
    d_ref = os.path.join(a.out, "referencia")
    os.makedirs(d_train, exist_ok=True)
    os.makedirs(d_ref, exist_ok=True)
    # newline="" y sin salto de línea: en Windows "\n" se escribe como "\r\n" y
    # Edge Impulse toma el "\r" como parte del nombre ("Abeja\r" != "Abeja").
    with open(os.path.join(d_train, "classes.txt"), "w", encoding="utf-8", newline="") as f:
        f.write("Abeja")

    n_boxes = 0
    for k in sorted(wanted):
        cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        name = f"{prefix}_f{k:05d}"
        cv2.imwrite(os.path.join(d_train, name + ".png"), frame)

        lines, boxes = [], []
        if detector is not None:
            for cx, cy, _ in cluster_centroids(detector.detect_raw(frame), merge_radius=a.merge_px):
                bw, bh = a.box_w, a.box_h
                lines.append(f"0 {cx / w:.6f} {cy / h:.6f} {bw / w:.6f} {bh / h:.6f}")
                boxes.append((int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2)))
        with open(os.path.join(d_train, name + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        n_boxes += len(lines)

        ref = frame.copy()
        for x0, y0, x1, y1 in boxes:
            cv2.rectangle(ref, (x0, y0), (x1, y1), (0, 255, 0), 2)
        for x, y in wanted[k]:
            cv2.circle(ref, (x, y), 45, (255, 0, 255), 3)
        cv2.putText(ref, f"frame {k}  t={k / fps:.2f}s  magenta = salida anotada, verde = pre-etiqueta",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(d_ref, name + ".jpg"), ref, [cv2.IMWRITE_JPEG_QUALITY, 85])

    cap.release()
    print(f"Salidas usadas (t < {a.split}s): {len(outs)}")
    print(f"Frames extraídos: {len(wanted)} -> {d_train}")
    if detector is not None:
        print(f"Cajas pre-etiquetadas: {n_boxes} (revisar y agregar las abejas que falten)")
    print(f"Imágenes de referencia: {d_ref}")


if __name__ == "__main__":
    main()
