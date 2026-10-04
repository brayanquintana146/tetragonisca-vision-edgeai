"""
Pruebas del contador híbrido (salidas por cruce, entradas por origen-destino)
con trayectorias sintéticas. Ejecutar:  python test_counter_hybrid.py   (o pytest)
"""
import numpy as np

from src.tracker import BeeTracker
from src.counter import BeeCounterHybrid

CX, CY, R, FPS = 500.0, 500.0, 100.0, 30


def run(path, t_end):
    """path: t -> (x, y) en radios relativos al centro de la ROI. Devuelve (in, out)."""
    tr = BeeTracker(scale=R)
    co = BeeCounterHybrid((CX, CY), R)
    for t in np.arange(0, t_end, 1.0 / FPS):
        x, y = path(t)
        active, finished = tr.update([(CX + x * R, CY + y * R, 0.9)], t)
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
        if t < 3.5:
            return (0.3 + (t - 3.0) * 3.0, 0.0)        # sale otra vez
        return (1.8, 0.0)
    assert run(path, 4.5)[1] == 2


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


if __name__ == "__main__":
    test_two_exits_same_track()
    test_peek_and_return_cancels()
    test_simple_entry()
    print("OK")
