"""
Corre el tracker v2 y el contador sobre detecciones guardadas con
bench/dump_detections.py, sin video ni modelo: tarda segundos en vez de minutos
y da exactamente lo mismo en cualquier PC con el mismo archivo.

Las opciones del tracker/contador son las mismas de main.py. El CSV de eventos
tiene el mismo formato que main.py --events, así que se evalúa igual:

  python bench/replay_detections.py det_pc.json.gz --counter hibrido --max-gate 0.6 \\
      --max-gate-tentative 1.2 --accel-std 80 --events eventos_replay.csv
  python bench/compare_events.py data/gt_0040-1.csv eventos_replay.csv --tol 0.5 --max-angle 40
"""
import argparse
import csv
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.counter import BeeCounterHybrid, BeeCounterV2  # noqa: E402
from src.detection import cluster_centroids  # noqa: E402
from src.tracker import BeeTracker  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Tracker + contador sobre detecciones guardadas")
    ap.add_argument("dets", help="archivo .json.gz de bench/dump_detections.py")
    ap.add_argument("--events", default="eventos_replay.csv")
    ap.add_argument("--roi-x", type=int, default=900)
    ap.add_argument("--roi-y", type=int, default=600)
    ap.add_argument("--roi-r", type=int, default=220)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--assoc-threshold", type=float, default=0.35)
    ap.add_argument("--max-lost", type=float, default=0.6)
    ap.add_argument("--max-gate", type=float, default=1.2)
    ap.add_argument("--max-gate-tentative", type=float, default=None)
    ap.add_argument("--accel-std", type=float, default=40.0)
    ap.add_argument("--counter", choices=["v2", "hibrido"], default="v2")
    ap.add_argument("--cancel-s", type=float, default=0.5)
    ap.add_argument("--proj-min-speed", type=float, default=1.5)
    ap.add_argument("--flash-exits", action="store_true")
    ap.add_argument("--track-scale", type=float, default=None)
    ap.add_argument("--core", type=float, default=None)
    a = ap.parse_args()

    with gzip.open(a.dets, "rt", encoding="utf-8") as f:
        data = json.load(f)
    info = data["info"]
    det_threshold = min(a.threshold, a.assoc_threshold)
    if info["threshold"] > det_threshold:
        raise SystemExit(f"Las detecciones se guardaron con umbral {info['threshold']}; "
                         f"hace falta <= {det_threshold}")
    fps = info["fps"]

    track_scale = a.track_scale or a.roi_r
    tracker = BeeTracker(scale=track_scale, max_lost_s=a.max_lost, birth_min_prob=a.threshold,
                         max_gate=a.max_gate, accel_std=a.accel_std, max_gate_tentative=a.max_gate_tentative)
    if a.counter == "hibrido":
        counter = BeeCounterHybrid(roi_center=(a.roi_x, a.roi_y), roi_radius=a.roi_r,
                                   cancel_s=a.cancel_s, proj_min_speed=a.proj_min_speed,
                                   flash_exits=a.flash_exits, track_scale=track_scale,
                                   core=a.core)
    else:
        counter = BeeCounterV2(roi_center=(a.roi_x, a.roi_y), roi_radius=a.roi_r)

    for i, frame_dets in enumerate(data["dets"]):
        raw = [tuple(d) for d in frame_dets if d[2] > det_threshold]
        centroids = cluster_centroids(raw, merge_radius=0.25 * track_scale)
        active, finished = tracker.update(centroids, i / fps)
        if a.flash_exits:
            counter.update(active, finished, detections=centroids, t=i / fps)
        else:
            counter.update(active, finished)
    if a.flash_exits:
        counter.update([], tracker.flush(), final=True)
    else:
        counter.update([], tracker.flush())

    with open(a.events, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "evento", "id", "x", "y"])
        for ev in counter.events:
            w.writerow([round(ev[0], 3), ev[1], ev[2], int(ev[3]), int(ev[4])])
    print(f"{info['platform']} | {len(data['dets'])} frames | IN {counter.in_count}  OUT {counter.out_count} "
          f"-> {a.events}")


if __name__ == "__main__":
    main()
