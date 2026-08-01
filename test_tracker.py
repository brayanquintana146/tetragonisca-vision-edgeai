from src.tracker import EuTrack

# 1. Inicializar el tracker
tracker = EuTrack(max_disappeared=5, max_distance=30)

print("--- Frame 1: Aparecen dos abejas ---")
frame1_centroids = [(100, 100), (200, 200)]
objects = tracker.update(frame1_centroids)
for obj_id, centroid in objects.items():
    print(f"Abeja ID {obj_id} en posición {centroid}")

print("\n--- Frame 2: Las abejas se mueven 5 píxeles ---")
frame2_centroids = [(105, 102), (202, 198)]
objects = tracker.update(frame2_centroids)
for obj_id, centroid in objects.items():
    print(f"Abeja ID {obj_id} se movió a {centroid}")

print("\n--- Frame 3 a 8: La abeja ID 1 desaparece (oclusión) ---")
frame3_centroids = [(110, 104)]  # Solo detectamos la primera
for f in range(3, 9):
    objects = tracker.update(frame3_centroids)

print(f"IDs activos tras desregistro por superar max_disappeared: {list(objects.keys())}")