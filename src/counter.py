import numpy as np


class BeeCounter:
    """
    Módulo de conteo de eventos de entrada y salida para abejas Jataí
    basado en región de interés (ROI) circular sobre la piquera.

    Incluye conteo inferido por desaparición: cuando una abeja desaparece
    del tracker mientras estaba dentro/cerca del ROI, se infiere la dirección
    del cruce basándose en su vector de velocidad.

    Referencia técnica:
    Leocádio et al., "Multiple Object Tracking in Native Bee Hives"
    """

    def __init__(self, roi_center, roi_radius):
        """
        roi_center: tuple (cx, cy) con el centro del círculo de la piquera
        roi_radius: int con el radio del círculo en píxeles
        """
        self.roi_center = np.array(roi_center, dtype="float")
        self.roi_radius = roi_radius

        self.in_count = 0
        self.out_count = 0

        # Conjunto unificado para evitar doble conteo y bloquear re-cruces oscilatorios
        # Un ID solo puede sumar UNA VEZ (ya sea IN o OUT) en toda su trayectoria
        self.counted = set()

    def _is_inside(self, centroid):
        """Calcula si un centroide (Cx, Cy) se encuentra dentro del círculo ROI."""
        dist = np.linalg.norm(np.array(centroid) - self.roi_center)
        return dist <= self.roi_radius

    def _is_near(self, centroid, margin=1.5):
        """Calcula si un centroide está cerca del ROI (dentro de margin * radio)."""
        dist = np.linalg.norm(np.array(centroid) - self.roi_center)
        return dist <= self.roi_radius * margin

    def _velocity_points_outward(self, position, velocity):
        """
        Verifica si el vector de velocidad apunta HACIA AFUERA del centro del ROI.
        Usa el producto punto entre el vector posición→afuera y la velocidad.
        """
        outward_dir = np.array(position) - self.roi_center
        return np.dot(outward_dir, velocity) > 0

    def update(self, objects, trajectories, deregistered=None):
        """
        Procesa las trayectorias de los objetos rastreados por EuTrack
        para detectar cruces de la frontera del círculo de la piquera.

        objects: OrderedDict {object_id: centroid}
        trajectories: OrderedDict {object_id: [(x1, y1), (x2, y2), ...]}
        deregistered: list of (last_pos, last_vel) from tracker deregistrations
        """
        # --- Conteo directo por cruce de frontera ---
        for object_id, history in trajectories.items():
            if object_id in self.counted:
                continue  # Bloqueo oscilatorio: este ID ya fue contado

            if len(history) < 2:
                continue

            prev_pos = history[-2]
            curr_pos = history[-1]

            prev_inside = self._is_inside(prev_pos)
            curr_inside = self._is_inside(curr_pos)

            # Entrada: la abeja estaba fuera y cruza hacia dentro de la piquera
            if not prev_inside and curr_inside:
                self.in_count += 1
                self.counted.add(object_id)

            # Salida: la abeja estaba dentro y cruza hacia fuera de la piquera
            elif prev_inside and not curr_inside:
                self.out_count += 1
                self.counted.add(object_id)

        # --- Conteo inferido por desaparición ---
        # Cuando una abeja desaparece del tracker cerca del ROI,
        # usamos su velocidad para inferir si entró o salió de la colmena.
        if deregistered:
            for object_id, last_pos, last_vel, hist_len in deregistered:
                if object_id in self.counted:
                    continue  # Ya fue contada de forma directa, ignorar inferencia

                # Filtrar ruido: solo inferir si la trayectoria duró al menos 5 frames
                if hist_len < 5:
                    continue

                speed = np.linalg.norm(last_vel)
                if speed < 2.0:
                    continue  # Velocidad muy baja, no inferir dirección

                if self._is_near(last_pos):
                    if self._velocity_points_outward(last_pos, last_vel):
                        # Velocidad apunta hacia afuera del ROI → salida
                        self.out_count += 1
                        self.counted.add(object_id)
                    else:
                        # Velocidad apunta hacia dentro del ROI → entrada
                        self.in_count += 1
                        self.counted.add(object_id)

        return {"in": self.in_count, "out": self.out_count}