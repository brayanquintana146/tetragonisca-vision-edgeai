"""
Prueba del tracker v1 (EuTrack).
Ejecutar: python test_tracker.py (o pytest)
"""
from src.tracker import EuTrack


def test_eutrack_lifecycle():
    tracker = EuTrack(max_disappeared=5, max_distance=30)

    print("--- Frame 1: Aparecen dos abejas ---")
    objects, deregistered = tracker.update([(100, 100), (200, 200)])
    for obj_id, centroid in objects.items():
        print(f"Abeja ID {obj_id} en posición {centroid}")
    assert list(objects.keys()) == [0, 1]
    assert deregistered == []

    print("\n--- Frame 2: Las abejas se mueven 5 píxeles ---")
    objects, deregistered = tracker.update([(105, 102), (202, 198)])
    for obj_id, centroid in objects.items():
        print(f"Abeja ID {obj_id} se movió a {centroid}")
    assert list(objects.keys()) == [0, 1]
    assert deregistered == []

    print("\n--- Frame 3 a 8: La abeja ID 1 desaparece (oclusión) ---")
    bajas = []
    for _ in range(3, 9):
        objects, deregistered = tracker.update([(110, 104)])  # solo se detecta la primera
        bajas.extend(deregistered)
    print(f"IDs activos tras desregistro por superar max_disappeared: {list(objects.keys())}")
    assert list(objects.keys()) == [0]
    assert len(bajas) == 1 and bajas[0][0] == 1


if __name__ == "__main__":
    test_eutrack_lifecycle()
    print("OK test_eutrack_lifecycle")
