"""
Compara los eventos del tracker (CSV de main.py --events) contra la anotación
manual (CSV de tools/anotar_eventos.py), evento por evento.

Un evento predicho es correcto (TP) si hay un evento anotado del MISMO tipo
a menos de --tol segundos que no haya sido usado por otro.
  FP: el tracker contó algo que no ocurrió (p. ej. una guardiana).
  FN: ocurrió y el tracker no lo contó (p. ej. una salida perdida).

Con --max-angle además debe estar del mismo lado de la ROI (ángulo alrededor de
--roi-x/--roi-y). La columna "F1 azar" es el F1 que se obtiene desplazando en el
tiempo los mismos eventos del tracker: si F1 no la supera con claridad, el
resultado no se distingue de contar al azar. Con ~1.3 salidas por segundo y ±1 s,
eventos al azar ya dan F1 ≈ 0.65; usar p. ej. --tol 0.5 --max-angle 40.

Uso:
  python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv
  python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv eventos_pi.csv --end 30
  python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv --tol 0.5 --max-angle 40
"""
import argparse
import csv
import math
import random


def load(path, start, end):
    ev = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = float(r["t_s"])
            if start <= t <= end:
                ev.append((t, r["evento"].strip().lower(), int(float(r.get("x", 0) or 0)), int(float(r.get("y", 0) or 0))))
    return sorted(ev)


def _angle(e, center):
    return math.degrees(math.atan2(e[3] - center[1], e[2] - center[0]))


def match(gt, pred, tol, max_angle=None, center=(900, 600)):
    """Emparejamiento por cercanía temporal: primero los pares más cercanos.
    Con max_angle, además el ángulo alrededor de la ROI debe diferir a lo sumo max_angle grados."""
    def same_side(g, p):
        return max_angle is None or abs((_angle(g, center) - _angle(p, center) + 180) % 360 - 180) <= max_angle
    pairs = sorted(
        (abs(g[0] - p[0]), i, j)
        for i, g in enumerate(gt) for j, p in enumerate(pred)
        if g[1] == p[1] and abs(g[0] - p[0]) <= tol and same_side(g, p)
    )
    used_g, used_p, tp = set(), set(), []
    for _, i, j in pairs:
        if i in used_g or j in used_p:
            continue
        used_g.add(i)
        used_p.add(j)
        tp.append((gt[i], pred[j]))
    fn = [g for i, g in enumerate(gt) if i not in used_g]
    fp = [p for j, p in enumerate(pred) if j not in used_p]
    return tp, fp, fn


def fmt(e):
    return f"{e[0]:6.2f}s ({e[2]},{e[3]})"


def _f1(gt, pred, tp, kind):
    g = sum(e[1] == kind for e in gt)
    p = sum(e[1] == kind for e in pred)
    t = sum(a[1] == kind for a, _ in tp)
    prec = t / p if p else 0.0
    rec = t / g if g else 0.0
    return prec, rec, (2 * prec * rec / (prec + rec) if prec + rec else 0.0)


def chance_f1(gt, pred, tol, max_angle, center, start, end, reps=100):
    """F1 medio desplazando los eventos del tracker en el tiempo (circularmente dentro
    de la ventana): conserva cuántos y dónde, pero rompe el cuándo."""
    span = end - start
    if span <= 2 * tol:
        return {"in": 0.0, "out": 0.0}
    acc = {"in": 0.0, "out": 0.0}
    for s in range(reps):
        off = random.Random(s).uniform(tol, span - tol)
        shifted = [(start + (e[0] - start + off) % span,) + tuple(e[1:]) for e in pred]
        tp, _, _ = match(gt, shifted, tol, max_angle, center)
        for kind in acc:
            acc[kind] += _f1(gt, shifted, tp, kind)[2] / reps
    return acc


def report(gt, pred, tol, name, verbose, max_angle=None, center=(900, 600), window=(0.0, 0.0)):
    tp, fp, fn = match(gt, pred, tol, max_angle, center)
    rnd = chance_f1(gt, pred, tol, max_angle, center, *window)
    print(f"\n=== {name} ===")
    print(f"{'':6s} {'anotado':>8s} {'tracker':>8s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'precision':>10s} {'recall':>8s} {'F1':>6s} {'F1 azar':>8s}")
    for kind in ("in", "out"):
        g = sum(e[1] == kind for e in gt)
        p = sum(e[1] == kind for e in pred)
        t = sum(a[1] == kind for a, _ in tp)
        f_p = sum(e[1] == kind for e in fp)
        f_n = sum(e[1] == kind for e in fn)
        prec, rec, f1 = _f1(gt, pred, tp, kind)
        print(f"{kind.upper():6s} {g:8d} {p:8d} {t:4d} {f_p:4d} {f_n:4d} {prec:10.2f} {rec:8.2f} {f1:6.2f} {rnd[kind]:8.2f}")
    if verbose:
        for kind in ("in", "out"):
            miss = [fmt(e) for e in fn if e[1] == kind]
            extra = [fmt(e) for e in fp if e[1] == kind]
            if miss:
                print(f"  {kind.upper()} perdidos (FN): " + ", ".join(miss))
            if extra:
                print(f"  {kind.upper()} de más   (FP): " + ", ".join(extra))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gt", help="CSV anotado a mano")
    ap.add_argument("pred", nargs="+", help="uno o más CSV de main.py --events")
    ap.add_argument("--tol", type=float, default=1.0, help="tolerancia temporal (s)")
    ap.add_argument("--start", type=float, default=0.0, help="evaluar desde este segundo")
    ap.add_argument("--end", type=float, default=None,
                    help="evaluar hasta este segundo (por defecto: último evento anotado + tol)")
    ap.add_argument("--max-angle", type=float, default=None,
                    help="exigir además el mismo lado de la ROI: diferencia de ángulo máxima en grados (p. ej. 40)")
    ap.add_argument("--roi-x", type=int, default=900)
    ap.add_argument("--roi-y", type=int, default=600)
    ap.add_argument("-q", "--quiet", action="store_true", help="no listar eventos perdidos / de más")
    a = ap.parse_args()

    gt = load(a.gt, a.start, float("inf") if a.end is None else a.end)
    end = a.end if a.end is not None else (max(e[0] for e in gt) + a.tol if gt else 0.0)
    gt = [e for e in gt if e[0] <= end]
    side = f" | mismo lado de la ROI (±{a.max_angle:g}°)" if a.max_angle is not None else ""
    print(f"Ventana evaluada: {a.start:.1f}s - {end:.1f}s | tolerancia ±{a.tol}s{side}")
    for p in a.pred:
        report(gt, load(p, a.start, end), a.tol, p, not a.quiet,
               a.max_angle, (a.roi_x, a.roi_y), (a.start, end))


if __name__ == "__main__":
    main()
