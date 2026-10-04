"""
Guarda las detecciones crudas de FOMO de cada frame en un .json.gz.

Sirve para ajustar el tracker/contador sin volver a correr el modelo, y para
comparar entre computadoras: el mismo modelo da detecciones algo distintas en
Windows/TensorFlow, Linux/LiteRT y la Raspberry Pi.

Ejemplo:
  python bench/dump_detections.py --model models/fomo_nuevo_int8.lite --crop-roi --out det_pc.json.gz
"""
import argparse
import gzip
import json
import os
import platform
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main as pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Detecciones crudas de FOMO por frame")
    ap.add_argument("--video", default="examples/videos/0040-1.mp4")
    ap.add_argument("--model", default="models/fomo_tetragonisca_int8.lite")
    ap.add_argument("--crop-roi", action="store_true")
    ap.add_argument("--roi-x", type=int, default=900)
    ap.add_argument("--roi-y", type=int, default=600)
    ap.add_argument("--threshold", type=float, default=0.2, help="guarda celdas sobre este umbral")
    ap.add_argument("--out", default="detecciones.json.gz")
    a = ap.parse_args()

    det = pipeline.FOMODetector(model_path=a.model, threshold=a.threshold, num_threads=4,
                                crop_center=(a.roi_x, a.roi_y) if a.crop_roi else None)
    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"No se pudo abrir {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append([[int(x), int(y), round(float(p), 4)] for x, y, p in det.detect_raw(frame)])
    cap.release()

    info = {
        "video": a.video, "model": os.path.basename(a.model), "crop_roi": a.crop_roi,
        "fps": fps, "threshold": a.threshold, "n_frames": len(frames),
        "platform": platform.platform(), "python": platform.python_version(),
        "opencv": cv2.__version__, "runtime": getattr(pipeline.tflite, "__name__", str(pipeline.tflite)),
    }
    with gzip.open(a.out, "wt", encoding="utf-8") as f:
        json.dump({"info": info, "dets": frames}, f)
    print(f"{len(frames)} frames -> {a.out}")
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
