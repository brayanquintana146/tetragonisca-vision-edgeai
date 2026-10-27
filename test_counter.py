"""
Prueba del contador v1 (BeeCounter) con EuTrack.
Ejecutar: python test_counter.py (o pytest)
"""
from src.counter import BeeCounter
from src.tracker import EuTrack


def test_beecounter_entry():
    tracker = EuTrack(max_disappeared=5, max_distance=50)
    # Círculo centrado en (150, 150) con radio de 40 píxeles
    counter = BeeCounter(roi_center=(150, 150), roi_radius=40)

    # Abeja que cruza de fuera (100, 150) hacia dentro (145, 150) -> entrada
    objs, dereg = tracker.update([(100, 150)])
    counter.update(objs, tracker.trajectories, deregistered=dereg)

    objs, dereg = tracker.update([(145, 150)])
    counts = counter.update(objs, tracker.trajectories, deregistered=dereg)

    print("Conteo tras cruce hacia adentro:", counts)
    assert counts == {"in": 1, "out": 0}


if __name__ == "__main__":
    test_beecounter_entry()
    print("OK test_beecounter_entry")
