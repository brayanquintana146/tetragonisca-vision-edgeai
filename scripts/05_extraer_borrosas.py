"""
Extrae frames con abejas EN MOVIMIENTO que el modelo NO detecta (abejas
borrosas al despegar o volar), sin anotar el video a mano.

Cómo las encuentra: compara cada frame con el anterior. Una mancha que se movió
cerca de la piquera y que FOMO no detecta es casi siempre una abeja borrosa.
También aparecen sombras u hojas: por eso cada imagen trae su referencia.

Salida (--out, por defecto data/borrosas/):
  train/        imágenes .png + etiquetas YOLO .txt + classes.txt ("Abeja"),
                lista para edge-impulse-uploader --dataset-format yolo-txt.
                Las imágenes son el recorte cuadrado centrado en la ROI, el
                mismo que ve el modelo con main.py --crop-roi.
  referencia/   mismas imágenes con la mancha en movimiento (círculo magenta; la abeja
                borrosa suele estar junto al círculo, no siempre dentro)
                y las cajas pre-etiquetadas (verde). NO se suben.

Antes de subir: abre referencia/ y BORRA de train/ (.png y .txt) los frames
donde el círculo magenta no marca una abeja. Al etiquetar en Edge Impulse,
pon caja a TODAS las abejas del frame, nítidas y borrosas.

No uses aquí el video con el que evalúas (0040-1): sus frames contaminarían la medición.

Uso (varios videos a la vez):
  python scripts/05_extraer_borrosas.py --model models/fomo_nuevo_int8.lite ^
      --videos C:\\videos_004\\*.mp4
"""
import argparse
import glob
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import FOMODetector  # noqa: E402
from src.detection import cluster_centroids  # noqa: E402


def motion_blobs(prev, cur, thr, min_area, max_area):
    """Centroides (x, y, área) de las manchas que cambiaron entre dos frames en gris."""
    diff = cv2.GaussianBlur(cv2.absdiff(cur, prev), (5, 5), 0)
    _, mask = cv2.threshold(diff, thr, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    return [(float(cents[i][0]), float(cents[i][1]), int(stats[i, cv2.CC_STAT_AREA]))
            for i in range(1, n) if min_area <= stats[i, cv2.CC_STAT_AREA] <= max_area]


def main():
    ap = argparse.ArgumentParser(description="Extrae frames con abejas borrosas que el modelo no detecta")
    ap.add_argument("--videos", nargs="+", required=True, help="videos o patrones (p. ej. C:\\videos\\*.mp4)")
    ap.add_argument("--model", default="models/fomo_nuevo_int8.lite")
    ap.add_argument("--out", default="data/borrosas")
    ap.add_argument("--roi-x", type=int, default=900)
    ap.add_argument("--roi-y", type=int, default=600)
    ap.add_argument("--roi-r", type=int, default=220)
    ap.add_argument("--zone", type=float, default=1.8, help="buscar manchas hasta este múltiplo del radio de la ROI")
    ap.add_argument("--assoc-threshold", type=float, default=0.35,
                    help="una mancha con una detección de al menos esta confianza cerca NO cuenta (ya se ve)")
    ap.add_argument("--near-px", type=int, default=70, help="distancia mancha-detección para darla por vista")
    ap.add_argument("--diff-thr", type=int, default=25, help="cambio mínimo de brillo entre frames (0-255)")
    ap.add_argument("--min-area", type=int, default=150, help="área mínima de la mancha (px del video)")
    ap.add_argument("--max-area", type=int, default=12000, help="área máxima (descarta cambios de luz)")
    ap.add_argument("--min-gap", type=int, default=20, help="frames mínimos entre dos frames guardados")
    ap.add_argument("--max-per-video", type=int, default=40)
    ap.add_argument("--box-w", type=int, default=59, help="ancho (px) de las cajas pre-etiquetadas")
    ap.add_argument("--box-h", type=int, default=80, help="alto (px) de las cajas pre-etiquetadas")
    a = ap.parse_args()

    paths = sorted({p for pat in a.videos for p in (glob.glob(pat) or [pat])})
    detector = FOMODetector(model_path=a.model, threshold=a.assoc_threshold, num_threads=4,
                            crop_center=(a.roi_x, a.roi_y))
    d_train = os.path.join(a.out, "train")
    d_ref = os.path.join(a.out, "referencia")
    os.makedirs(d_train, exist_ok=True)
    os.makedirs(d_ref, exist_ok=True)
    # Sin salto de línea: en Windows "\n" se vuelve "\r\n" y Edge Impulse lee "Abeja\r"
    with open(os.path.join(d_train, "classes.txt"), "w", encoding="utf-8", newline="") as f:
        f.write("Abeja")

    total = 0
    for path in paths:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"[AVISO] No se pudo abrir {path}")
            continue
        prefix = os.path.splitext(os.path.basename(path))[0]
        prev, last_saved, saved, k = None, -10 ** 9, 0, -1
        while saved < a.max_per_video:
            ok, frame = cap.read()
            if not ok:
                break
            k += 1
            gray = cv2.cvtColor(cv2.resize(frame, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
            if prev is None or k - last_saved < a.min_gap:
                prev = gray
                continue
            blobs = [(2 * x, 2 * y, 4 * ar) for x, y, ar in
                     motion_blobs(prev, gray, a.diff_thr, a.min_area / 4, a.max_area / 4)]
            prev = gray
            blobs = [b for b in blobs if math.hypot(b[0] - a.roi_x, b[1] - a.roi_y) <= a.zone * a.roi_r]
            if not blobs:
                continue
            raw = detector.detect_raw(frame)
            unseen = [b for b in blobs
                      if not any(math.hypot(b[0] - cx, b[1] - cy) <= a.near_px for cx, cy, _ in raw)]
            if not unseen:
                continue

            # Recorte cuadrado centrado en la ROI (lo mismo que ve el modelo con --crop-roi)
            x0, y0, side, _ = detector.crop_box(frame.shape[1], frame.shape[0])
            crop = frame[y0:y0 + side, x0:x0 + side]
            name = f"{prefix}_f{k:05d}"
            cv2.imwrite(os.path.join(d_train, name + ".png"), crop)

            lines, ref = [], crop.copy()
            for cx, cy, *_ in cluster_centroids([d for d in raw if d[2] >= 0.55], merge_radius=0.25 * a.roi_r):
                lx, ly = cx - x0, cy - y0
                if 0 <= lx < side and 0 <= ly < side:
                    lines.append(f"0 {lx / side:.6f} {ly / side:.6f} {a.box_w / side:.6f} {a.box_h / side:.6f}")
                    cv2.rectangle(ref, (int(lx - a.box_w / 2), int(ly - a.box_h / 2)),
                                  (int(lx + a.box_w / 2), int(ly + a.box_h / 2)), (0, 255, 0), 2)
            with open(os.path.join(d_train, name + ".txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
            for bx, by, _ in unseen:
                cv2.circle(ref, (int(bx - x0), int(by - y0)), 45, (255, 0, 255), 3)
            cv2.putText(ref, f"{name}  magenta = movimiento no detectado, verde = pre-etiqueta",
                        (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imwrite(os.path.join(d_ref, name + ".jpg"), ref, [cv2.IMWRITE_JPEG_QUALITY, 85])
            last_saved, saved = k, saved + 1
        cap.release()
        print(f"{prefix}: {saved} frames")
        total += saved

    print(f"Total: {total} frames -> {d_train}")
    print(f"Revisa {d_ref} y borra de train/ los frames donde el círculo magenta no es una abeja.")


if __name__ == "__main__":
    main()
