from src.tracker import EuTrack
from src.counter import BeeCounter

tracker = EuTrack(max_disappeared=5, max_distance=50)
# Círculo centrado en (150, 150) con radio de 40 píxeles
counter = BeeCounter(roi_center=(150, 150), roi_radius=40)

# Simular abeja cruzando de fuera (100, 150) hacia dentro (145, 150) -> Entrada
frame1 = [(100, 150)]
objs1 = tracker.update(frame1)

frame2 = [(145, 150)]
objs2 = tracker.update(frame2)

counts = counter.update(objs2, tracker.trajectories)
print("Conteo tras cruce hacia adentro:", counts)