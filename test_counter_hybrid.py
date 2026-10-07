"""
Pruebas del contador híbrido (salidas por cruce, entradas por origen-destino)
con trayectorias sintéticas. Ejecutar:  python test_counter_hybrid.py   (o pytest)
"""
import numpy as np

from src.tracker import BeeTracker
from src.counter import BeeCounterHybrid

CX, CY, R, FPS = 500.0, 500.0, 100.0, 30


def run(path, t_end, tracker_kw=None, **kw):
    """path: t -> (x, y) en radios relativos al centro de la ROI, o None si no se ve. Devuelve (in, out)."""
    tr = BeeTracker(scale=R, **(tracker_kw or {}))
    co = BeeCounterHybrid((CX, CY), R, **kw)
    for t in np.arange(0, t_end, 1.0 / FPS):
        p = path(t)
        dets = [] if p is None else [(CX + p[0] * R, CY + p[1] * R, 0.9)]
        active, finished = tr.update(dets, t)
        co.update(active, finished)
    co.update([], tr.flush())
    return co.in_count, co.out_count


def test_two_exits_same_track():
    # Un mismo track sale, vuelve caminando y sale otra vez (p. ej. un track que
    # pasa de una abeja a otra): con V2 contaría 1 salida, aquí cuenta 2.
    def path(t):
        if t < 1.0:
            return (0.3, 0.0)
        if t < 1.5:
            return (0.3 + (t - 1.0) * 3.0, 0.0)        # sale hasta 1.8 r
        if t < 3.0:
            return (1.8 - (t - 1.5) * 1.0, 0.0)        # vuelve despacio hasta 0.3 r
        if t < 4.0:
            return (0.3, 0.0)                          # se queda dentro
        if t < 4.5:
            return (0.3 + (t - 4.0) * 3.0, 0.0)        # sale otra vez
        return (1.8, 0.0)
    assert run(path, 5.5)[1] == 2


def test_peek_and_return_cancels():
    # Se asoma fuera del borde y vuelve en menos de cancel_s: no cuenta nada.
    def path(t):
        if t < 1.0:
            return (0.3, 0.0)
        if t < 1.4:
            return (0.3 + (t - 1.0) * 3.0, 0.0)        # llega a 1.5 r
        if t < 1.8:
            return (1.5 - (t - 1.4) * 3.0, 0.0)        # vuelve a 0.3 r
        return (0.3, 0.0)
    assert run(path, 3.0) == (0, 0)


def test_simple_entry():
    def path(t):
        return (max(2.0 - t * 2.0, 0.2), 0.0)          # entra desde 2 r y se queda
    assert run(path, 2.0) == (1, 0)


def test_old_track_does_not_enter():
    # Revolotea fuera 5 s y luego entra: con in_max_age no cuenta (guardiana o punto del fondo).
    def path(t):
        if t < 5.0:
            return (2.0 + 0.3 * np.sin(6.0 * t), 0.0)
        return (max(2.0 - (t - 5.0) * 2.0, 0.2), 0.0)
    assert run(path, 7.0) == (1, 0)
    assert run(path, 7.0, in_max_age=3.0) == (0, 0)


def test_parked_point_jump_is_not_an_entry():
    # Un punto quieto fuera de la ROI 1 s; se apaga y el track salta a una abeja en la piquera.
    def path(t):
        if t < 1.0:
            return (1.3, 0.0)
        if t < 1.15:
            return None
        return (0.4, 0.0)
    kw = dict(tracker_kw=dict(accel_std=260.0))
    assert run(path, 2.0, **kw) == (1, 0)
    assert run(path, 2.0, in_park_s=0.15, **kw) == (0, 0)


def run_flashes(flashes, rep_s=None, t_end=30.0):
    """flashes: {frame: (x, y)} detecciones sueltas fuera de la ROI, en radios. Devuelve las salidas."""
    co = BeeCounterHybrid((CX, CY), R, flash_exits=True, rep_s=rep_s)
    for i, t in enumerate(np.arange(0, t_end, 1.0 / FPS)):
        dets = [(CX + flashes[i][0] * R, CY + flashes[i][1] * R, 0.5)] if i in flashes else []
        co.update([], [], detections=dets, t=t)
    co.update([], [], final=True)
    return co.out_count


def test_fixed_spot_repeated():
    # Un punto del fondo que se enciende 8 veces en el mismo sitio, cada 3 s: sin rep_s son
    # 8 salidas falsas; con rep_s solo pasan las 2 primeras (todavía no hay 2 marcas).
    flashes = {FPS * (1 + 3 * k): (2.0, 0.0) for k in range(8)}
    assert run_flashes(flashes) == 8
    assert run_flashes(flashes, rep_s=60) == 2


def test_flashes_elsewhere_still_count():
    # Despegues en sitios distintos: rep_s no quita ninguno.
    flashes = {FPS * (1 + 3 * k): (2.0, 0.3 * k - 1.0) for k in range(8)}
    assert run_flashes(flashes, rep_s=60) == 8


def test_still_flash_is_not_a_takeoff():
    # Un destello quieto 2 frames seguidos no es una abeja que despega.
    flashes = {FPS: (2.0, 0.0), FPS + 1: (2.0, 0.0)}
    assert run_flashes(flashes) == 1
    assert run_flashes(flashes, rep_s=60) == 0


if __name__ == "__main__":
    test_two_exits_same_track()
    test_peek_and_return_cancels()
    test_simple_entry()
    test_old_track_does_not_enter()
    test_parked_point_jump_is_not_an_entry()
    test_fixed_spot_repeated()
    test_flashes_elsewhere_still_count()
    test_still_flash_is_not_a_takeoff()
    print("OK")
