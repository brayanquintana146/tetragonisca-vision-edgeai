import numpy as np


class BeeCounter:
    """
    Módulo de conteo de eventos de entrada y salida para abejas Jataí
    basado en región de interés (ROI) circular sobre la piquera.

    Referencia técnica:
    Leocádio et al., "Multiple Object Tracking in Native Bee Hives: A Case Study with Jataí in the Field"
    """

    def __init__(self, roi_center, roi_radius):
        """
        roi_center: tuple (cx, cy) con el centro del círculo de la piquera
        roi_radius: int con el radio del círculo en píxeles
        """
        self.roi_center = np.array(roi_center)
        self.roi_radius = roi_radius

        self.in_count = 0
        self.out_count = 0

        # Conjuntos para evitar contar el mismo ID múltiples veces
        self.counted_in = set()
        self.counted_out = set()

    def _is_inside(self, centroid):
        """Calcula si un centroide (Cx, Cy) se encuentra dentro del círculo ROI."""
        dist = np.linalg.norm(np.array(centroid) - self.roi_center)
        return dist <= self.roi_radius

    def update(self, objects, trajectories):
        """
        Procesa las trayectorias de los objetos rastreados por EuTrack
        para detectar cruces de la frontera del círculo de la piquera.
        
        objects: OrderedDict {object_id: centroid}
        trajectories: OrderedDict {object_id: [(x1, y1), (x2, y2), ...]}
        """
        for object_id, history in trajectories.items():
            if len(history) < 2:
                continue

            prev_pos = history[-2]
            curr_pos = history[-1]

            prev_inside = self._is_inside(prev_pos)
            curr_inside = self._is_inside(curr_pos)

            # Entrada: la abeja estaba fuera y cruza hacia dentro de la piquera
            if not prev_inside and curr_inside:
                if object_id not in self.counted_in:
                    self.in_count += 1
                    self.counted_in.add(object_id)

            # Salida: la abeja estaba dentro y cruza hacia fuera de la piquera
            if prev_inside and not curr_inside:
                if object_id not in self.counted_out:
                    self.out_count += 1
                    self.counted_out.add(object_id)

        return {"in": self.in_count, "out": self.out_count}