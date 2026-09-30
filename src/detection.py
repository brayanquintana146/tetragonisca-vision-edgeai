"""
Utilidades de post-procesamiento de la salida de FOMO.
"""


def cluster_centroids(raw_centroids, merge_radius):
    """
    Agrupa celdas de FOMO que pertenecen a la misma abeja.

    raw_centroids: lista de (cx, cy, prob) en píxeles del frame.
    merge_radius:  distancia (px) bajo la cual dos celdas se fusionan. Debe
                   escalar con la resolución (p. ej. 0.25 * radio de la ROI);
                   un valor fijo en px fusiona abejas vecinas en resoluciones bajas.

    Devuelve lista de (cx, cy, prob_max) con centroide ponderado por confianza.
    """
    if not raw_centroids:
        return []
    pts = sorted(raw_centroids, key=lambda c: c[2], reverse=True)
    used = [False] * len(pts)
    r2 = merge_radius * merge_radius
    merged = []
    for i, (xi, yi, pi) in enumerate(pts):
        if used[i]:
            continue
        used[i] = True
        sx, sy, sw = xi * pi, yi * pi, pi
        for j in range(i + 1, len(pts)):
            if used[j]:
                continue
            xj, yj, pj = pts[j]
            # distancia al ancla (la celda más fuerte), no al promedio: evita
            # que el cluster "camine" y se trague abejas vecinas
            if (xi - xj) ** 2 + (yi - yj) ** 2 <= r2:
                sx += xj * pj
                sy += yj * pj
                sw += pj
                used[j] = True
        merged.append((sx / sw, sy / sw, pi))
    return merged
