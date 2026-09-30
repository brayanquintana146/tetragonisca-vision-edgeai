"""
Compara los eventos del tracker (CSV de main.py --events) contra la anotación
manual (CSV de tools/anotar_eventos.py), evento por evento.

Un evento predicho es correcto (TP) si hay un evento anotado del MISMO tipo
a menos de --tol segundos que no haya sido usado por otro.
  FP: el tracker contó algo que no ocurrió (p. ej. una guardiana).
  FN: ocurrió y el tracker no lo contó (p. ej. una salida perdida).

Uso:
  python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv
  python bench/compare_events.py data/gt_0040-1.csv eventos_v2.csv eventos_pi.csv --end 30
"""
import argparse
import csv


def load(path, start, end):
    ev = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = float(r["t_s"])
            if start <= t <= end:
                ev.append((t, r["evento"].strip().lower(), int(float(r.get("x", 0) or 0)), int(float(r.get("y", 0) or 0))))
    return sorted(ev)


def match(gt, pred, tol):
    """Emparejamiento por cercanía temporal: primero los pares más cercanos."""
    pairs = sorted(
        (abs(g[0] - p[0]), i, j)
        for i, g in enumerate(gt) for j, p in enumerate(pred)
        if g[1] == p[1] and abs(g[0] - p[0]) <= tol
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


def report(gt, pred, tol, name, verbose):
    tp, fp, fn = match(gt, pred, tol)
    print(f"\n=== {name} ===")
    print(f"{'':6s} {'anotado':>8s} {'tracker':>8s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'precision':>10s} {'recall':>8s} {'F1':>6s}")
    for kind in ("in", "out"):
        g = sum(e[1] == kind for e in gt)
        p = sum(e[1] == kind for e in pred)
        t = sum(a[1] == kind for a, _ in tp)
        f_p = sum(e[1] == kind for e in fp)
        f_n = sum(e[1] == kind for e in fn)
        prec = t / p if p else 0.0
        rec = t / g if g else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        print(f"{kind.upper():6s} {g:8d} {p:8d} {t:4d} {f_p:4d} {f_n:4d} {prec:10.2f} {rec:8.2f} {f1:6.2f}")
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
    ap.add_argument("-q", "--quiet", action="store_true", help="no listar eventos perdidos / de más")
    a = ap.parse_args()

    gt = load(a.gt, a.start, float("inf") if a.end is None else a.end)
    end = a.end if a.end is not None else (max(e[0] for e in gt) + a.tol if gt else 0.0)
    gt = [e for e in gt if e[0] <= end]
    print(f"Ventana evaluada: {a.start:.1f}s - {end:.1f}s | tolerancia ±{a.tol}s")
    for p in a.pred:
        report(gt, load(p, a.start, end), a.tol, p, not a.quiet)


if __name__ == "__main__":
    main()
