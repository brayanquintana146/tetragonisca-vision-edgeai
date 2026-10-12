"""
Mide el DETECTOR (sin tracker) en el momento de cada evento anotado.

Para cada entrada/salida de la verdad de campo, cuenta en cuántos frames
alrededor del cruce (±--window) hay una detección de FOMO a menos de --radius px
del punto anotado. Sirve para separar si un problema es del modelo o del tracker.

Ejemplo (compara frame completo vs recorte en la ROI con el mismo modelo):
  python bench/detection_at_events.py --model models/v4_fomo_nuevo_int8.lite
"""
import argparse
import csv
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import FOMODetector  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Detección de FOMO alrededor de cada evento anotado")
    ap.add_argument("--gt", default="data/gt_0040-1.csv")
    ap.add_argument("--video", default="examples/videos/0040-1.mp4")
    ap.add_argument("--model", default="models/v3_fomo_tetragonisca_int8.lite")
    ap.add_argument("--roi-x", type=int, default=900)
    ap.add_argument("--roi-y", type=int, default=600)
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--window", type=int, default=6, help="frames antes y después del cruce")
    ap.add_argument("--radius", type=int, default=120, help="px alrededor del punto anotado")
    ap.add_argument("--min-frames", type=int, default=3, help="frames con detección para darlo por visto")
    ap.add_argument("--start", type=float, default=0.0, help="solo eventos desde este segundo")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"No se pudo abrir {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    events = []
    with open(a.gt, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if float(r["t_s"]) < a.start:
                continue
            fr = int(r["frame"]) if r.get("frame") else int(round(float(r["t_s"]) * fps))
            events.append((r["evento"].strip().lower(), fr, int(r["x"]), int(r["y"])))

    needed = {k for _, fr, _, _ in events for k in range(fr - a.window, fr + a.window + 1)}
    frames, i = {}, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i in needed:
            frames[i] = frame
        i += 1
    cap.release()

    n_win = 2 * a.window + 1
    print(f"Modelo: {a.model} | umbral {a.threshold} | ±{a.window} frames | radio {a.radius} px")
    for name, center in (("frame completo", None), ("recorte ROI", (a.roi_x, a.roi_y))):
        det = FOMODetector(model_path=a.model, threshold=a.threshold, num_threads=4, crop_center=center)
        dets = {k: det.detect_raw(v) for k, v in frames.items()}
        for kind in ("in", "out"):
            hits = np.array([
                sum(1 for k in range(fr - a.window, fr + a.window + 1)
                    if any((cx - x) ** 2 + (cy - y) ** 2 <= a.radius ** 2 for cx, cy, _ in dets.get(k, ())))
                for ev, fr, x, y in events if ev == kind
            ])
            if len(hits) == 0:
                continue
            print(f"  {name:15s} {kind.upper():3s} n={len(hits):3d}  visto en >={a.min_frames} de {n_win} frames: "
                  f"{np.mean(hits >= a.min_frames):4.0%}   frames con detección (promedio): {hits.mean():.1f}")


if __name__ == "__main__":
    main()
