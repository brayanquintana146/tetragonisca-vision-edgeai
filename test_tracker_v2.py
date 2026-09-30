"""
Pruebas del tracker v2 (BeeTracker) y del contador v2 (BeeCounterV2)
con trayectorias sintéticas. Ejecutar:  python test_tracker_v2.py   (o pytest)
"""
import numpy as np

from src.tracker import BeeTracker
from src.counter import BeeCounterV2


def simulate(paths, fps, roi=(500, 500, 100), scale_px=1.0, t_end=None, miss_every=0):
    """
    paths: lista de funciones t -> (x, y) | None  (None = la abeja no se ve)
    Coordenadas en 'radios' relativas al centro de la ROI; se escalan a px.
    Devuelve (in, out, confirmed_total).
    """
    cx, cy, r = roi[0] * scale_px, roi[1] * scale_px, roi[2] * scale_px
    tr = BeeTracker(scale=r)
    co = BeeCounterV2((cx, cy), r)
    t_end = t_end or 3.0
    k = 0
    for t in np.arange(0, t_end, 1.0 / fps):
        k += 1
        dets = []
        for p in paths:
            q = p(t)
            if q is None:
                continue
            if miss_every and k % miss_every == 0:
                continue
            dets.append((cx + q[0] * r, cy + q[1] * r, 0.9))
        active, finished = tr.update(dets, float(t))
        co.update(active, finished)
    co.update([], tr.flush())
    return co.in_count, co.out_count, tr.confirmed_total


# --- Trayectorias típicas (unidades: radios de la ROI, t en segundos) -------

def exiting_bee(t0=0.5):
    """Camina desde el tubo y despega: FOMO la pierde a 0.8 r (desenfoque),
    antes de que cruce el borde de la ROI."""
    def p(t):
        if t < t0:
            return None
        s = t - t0
        if s < 0.6:                       # camina hacia afuera
            return (0.1 + 0.6 * s, 0.0)
        d = 0.46 + 3.0 * (s - 0.6)        # despega a 3 radios/s
        return (d, 0.0) if d < 0.8 else None
    return p


def entering_bee(t0=0.5):
    """Llega volando desde afuera, aterriza y entra al tubo."""
    def p(t):
        if t < t0:
            return None
        s = t - t0
        d = 2.5 - 5.0 * s if s < 0.36 else 0.7 - 0.8 * (s - 0.36)
        return (0.0, d) if d > 0.05 else None
    return p


def guard_bee():
    """Guardiana que oscila sobre el borde de la ROI todo el tiempo."""
    return lambda t: (1.0 + 0.12 * np.sin(2 * np.pi * 1.5 * t), 0.0)


def hovering_bee():
    """Revolotea fuera de la ROI y se va sin entrar."""
    return lambda t: (-1.8 + 0.3 * np.sin(4 * t), 1.2) if t < 2.5 else None


# --- Pruebas ----------------------------------------------------------------

def test_exit_counted_at_any_fps():
    for fps in (60, 30, 15, 10):
        i, o, _ = simulate([exiting_bee()], fps)
        assert (i, o) == (0, 1), f"salida a {fps} fps: IN={i} OUT={o}"


def test_entry_counted_at_any_fps():
    for fps in (60, 30, 15, 10):
        i, o, _ = simulate([entering_bee()], fps)
        assert (i, o) == (1, 0), f"entrada a {fps} fps: IN={i} OUT={o}"


def test_resolution_invariance():
    """Los mismos movimientos en 1080p y en 640x480 dan el mismo conteo."""
    paths = [exiting_bee(0.3), entering_bee(1.0), guard_bee()]
    a = simulate(paths, 30, scale_px=1.0)
    b = simulate(paths, 30, scale_px=640 / 1920)
    assert a[:2] == b[:2] == (1, 1), (a, b)


def test_guard_and_hovering_not_counted():
    i, o, _ = simulate([guard_bee(), hovering_bee()], 30)
    assert (i, o) == (0, 0), f"IN={i} OUT={o}"


def test_missed_detections_keep_identity():
    """Con 1 de cada 3 detecciones perdidas la abeja sigue siendo un solo ID."""
    i, o, n = simulate([exiting_bee()], 30, miss_every=3)
    assert (i, o, n) == (0, 1, 1), (i, o, n)


def test_crossing_bees_keep_identity():
    """Dos abejas que se cruzan no intercambian identidad."""
    a = lambda t: (-1.5 + 1.0 * t, 0.05)
    b = lambda t: (1.5 - 1.0 * t, -0.05)
    tr = BeeTracker(scale=100)
    ids_left = set()
    for t in np.arange(0, 3.0, 1 / 15):
        dets = [(500 + a(t)[0] * 100, 500 + a(t)[1] * 100), (500 + b(t)[0] * 100, 500 + b(t)[1] * 100)]
        active, _ = tr.update(dets, float(t))
        for trk in active:
            if trk.vel[0] > 0:       # la que viaja hacia la derecha
                ids_left.add(trk.id)
    assert len(ids_left) == 1, ids_left


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK  {name}")
    print("Todas las pruebas pasaron.")
