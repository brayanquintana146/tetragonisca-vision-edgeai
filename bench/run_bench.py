"""
Banco de pruebas de tracking + conteo sobre detecciones FOMO cacheadas.

Compara el pipeline v1 (EuTrack + BeeCounter) y v2 (BeeTracker + BeeCounterV2)
en escenarios que simulan distintas condiciones de captura, contra la
conteo agregado de referencia del video 0040-1: fila 'Pseudo' de la Tabla 1 de
Leocádio et al. (42 IN / 85 OUT; conteo humano asistido, probablemente incluye
cruces de guardianas). Es solo orientativo: la evaluación de exactitud se hace
evento por evento con bench/compare_events.py contra una anotación manual.

Uso: python bench/run_bench.py --cache bench/cache/
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GT_IN, GT_OUT = 42, 85   # 'Pseudo', Tabla 1 del paper (orientativo)

# (nombre, archivo cache, procesar 1 de cada N frames, fracción de frames perdidos al azar)
SCENARIOS = [
    ('video 1080p @60',          'orig',        1, 0.0),
    ('video 1080p @30 (skip2)',  'orig',        2, 0.0),
    ('webcam 640x480 @15',       'webcam',      2, 0.0),
    ('webcam @15 + jitter 25%',  'webcam',      2, 0.25),
    ('webcam @10',               'webcam',      3, 0.0),
    ('webcam oscura @7.5',       'webcam_dark', 2, 0.0),
]


def grid_to_centroids(grid, box, threshold):
    """Celdas de FOMO sobre el umbral -> (cx, cy, prob) en px del frame completo."""
    gh, gw = grid.shape
    x0, y0, bw, bh = box
    ys, xs = np.nonzero(grid > threshold)
    return [(x0 + (x + 0.5) * bw / gw, y0 + (y + 0.5) * bh / gh, float(grid[y, x])) for y, x in zip(ys, xs)]


def load(cache, name, step, drop, phase=0, seed=0):
    d = np.load(os.path.join(cache, name + '.npz'))
    idx = np.arange(phase, len(d['times']), step)
    if drop > 0:
        rng = np.random.default_rng(seed)
        idx = idx[rng.random(len(idx)) >= drop]
    return d['grids'][idx].astype(np.float32), d['times'][idx], tuple(int(v) for v in d['box']), tuple(float(v) for v in d['roi'])


def variants(step, drop):
    """Todas las fases del submuestreo (y 5 semillas si hay frames perdidos):
    el resultado de una sola fase puede variar varias abejas por azar."""
    seeds = range(5) if drop > 0 else [0]
    return [(ph, sd) for ph in range(step) for sd in seeds]


def run_v1(grids, times, box, roi, threshold=0.55):
    from main import FOMODetector
    from src.tracker import EuTrack
    from src.counter import BeeCounter
    tr = EuTrack(max_disappeared=20, max_distance=250)
    co = BeeCounter((roi[0], roi[1]), roi[2])
    c = {'in': 0, 'out': 0}
    for g in grids:
        cents = FOMODetector._cluster_centroids(grid_to_centroids(g, box, threshold), merge_radius=60)
        objs, dereg = tr.update(cents)
        c = co.update(objs, tr.trajectories, deregistered=dereg)
    return c['in'], c['out'], tr.next_object_id


def run_v2(grids, times, box, roi, threshold=0.35, merge=0.25, counter_kw=None, **kw):
    from src.detection import cluster_centroids
    from src.tracker import BeeTracker
    from src.counter import BeeCounterV2
    scale = roi[2]
    tr = BeeTracker(scale=scale, **kw)
    co = BeeCounterV2((roi[0], roi[1]), roi[2], **(counter_kw or {}))
    for g, t in zip(grids, times):
        cents = cluster_centroids(grid_to_centroids(g, box, threshold), merge_radius=merge * scale)
        tracks, finished = tr.update(cents, t)
        co.update(tracks, finished)
    co.update([], tr.flush())
    return co.in_count, co.out_count, tr.confirmed_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default='bench/cache')
    ap.add_argument('--only', choices=['v1', 'v2'], default=None)
    a = ap.parse_args()
    runners = {'v1': run_v1, 'v2': run_v2}
    if a.only:
        runners = {a.only: runners[a.only]}
    print(f"Referencia de campo: {GT_IN} IN / {GT_OUT} OUT. Promedio ± desv. sobre fases del submuestreo.")
    print(f"{'Escenario':28s} | " + ' | '.join(f'{k}:    IN          OUT       err' for k in runners))
    tot = {k: 0.0 for k in runners}
    for label, name, step, drop in SCENARIOS:
        row = []
        for k, fn in runners.items():
            res = np.array([fn(*load(a.cache, name, step, drop, ph, sd))[:2] for ph, sd in variants(step, drop)])
            i, o = res.mean(0)
            err = np.mean(np.abs(res[:, 0] - GT_IN) + np.abs(res[:, 1] - GT_OUT))
            tot[k] += err
            row.append(f'{k}: {i:5.1f}±{res[:, 0].std():3.1f} {o:5.1f}±{res[:, 1].std():3.1f} {err:5.1f}')
        print(f'{label:28s} | ' + ' | '.join(row))
    print(f'Error medio total (|IN-{GT_IN}|+|OUT-{GT_OUT}|): ' + ', '.join(f'{k}={v:.0f}' for k, v in tot.items()))


if __name__ == '__main__':
    main()
