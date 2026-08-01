import numpy as np
from scipy.spatial import distance as dist
from scipy.optimize import linear_sum_assignment
from collections import OrderedDict


class EuTrack:
    """
    Algoritmo de seguimiento de centroides basado en distancia euclidiana (EuTrack).
    Asocia detecciones de centroides (Cx, Cy) producidas por FOMO entre fotogramas
    consecutivos y asigna identificadores (IDs) únicos.

    Incluye:
    - Predicción de velocidad para mantener IDs estables en movimiento rápido.
    - Suavizado adaptativo: bajo para abejas rápidas, alto para abejas lentas.
    - Limitación de longitud de trayectoria para control de memoria.

    Referencia: Leocádio et al., "Multiple Object Tracking in Native Bee Hives"
    """

    def __init__(self, max_disappeared=20, max_distance=250, max_trail=30):
        """
        max_disappeared: frames sin detección antes de eliminar el ID.
        max_distance:    distancia máxima (px) para asociar un centroide al mismo ID.
        max_trail:       cantidad máxima de puntos guardados en la trayectoria.
        """
        self.next_object_id = 0
        self.objects = OrderedDict()        # {id: np.array([cx, cy])}
        self.velocities = OrderedDict()     # {id: np.array([vx, vy])}
        self.disappeared = OrderedDict()    # {id: int}
        self.trajectories = OrderedDict()   # {id: [(x,y), ...]}
        # Snapshots del ultimo frame donde el objeto fue detectado realmente
        self.last_active_pos = OrderedDict()  # {id: np.array([cx, cy])}
        self.last_active_vel = OrderedDict()  # {id: np.array([vx, vy])}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.max_trail = max_trail

    def register(self, centroid):
        centroid_float = np.array(centroid, dtype="float")
        self.objects[self.next_object_id] = centroid_float
        self.velocities[self.next_object_id] = np.array([0.0, 0.0])
        self.disappeared[self.next_object_id] = 0
        self.trajectories[self.next_object_id] = [tuple(centroid_float.astype(int))]
        self.last_active_pos[self.next_object_id] = centroid_float.copy()
        self.last_active_vel[self.next_object_id] = np.array([0.0, 0.0])
        self.next_object_id += 1

    def deregister(self, object_id):
        """Elimina un objeto. Retorna posicion/velocidad/longitud del ultimo frame ACTIVO."""
        last_pos = self.last_active_pos[object_id].copy()
        last_vel = self.last_active_vel[object_id].copy()
        history_len = len(self.trajectories[object_id])
        del self.objects[object_id]
        del self.velocities[object_id]
        del self.disappeared[object_id]
        del self.trajectories[object_id]
        del self.last_active_pos[object_id]
        del self.last_active_vel[object_id]
        return last_pos, last_vel, history_len

    def _predict(self, object_id):
        """Predice la próxima posición del objeto usando su velocidad actual."""
        return self.objects[object_id] + self.velocities[object_id]

    def _adaptive_smooth(self, old_pos, new_pos, velocity):
        """
        Suavizado adaptativo: cuando la abeja vuela rápido (velocidad alta),
        se usa menos suavizado (alpha alto) para no quedarse atrás.
        Cuando camina lento, se usa más suavizado para estabilizar.
        """
        speed = np.linalg.norm(velocity)
        # alpha varía de 0.3 (lento, muy suave) a 0.9 (rápido, muy reactivo)
        alpha = min(0.9, 0.3 + speed / 100.0)
        return old_pos * (1 - alpha) + np.array(new_pos, dtype="float") * alpha

    def update(self, input_centroids):
        deregistered = []  # Lista de (last_pos, last_vel) de objetos eliminados

        if len(input_centroids) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                # Avanzar posición según velocidad, pero frenar fuertemente (0.4)
                # para que el punto predicho no se aleje mucho de donde desapareció
                self.objects[object_id] = self._predict(object_id)
                self.velocities[object_id] *= 0.4  # Freno fuerte
                if self.disappeared[object_id] > self.max_disappeared:
                    last_pos, last_vel, hist_len = self.deregister(object_id)
                    deregistered.append((object_id, last_pos, last_vel, hist_len))
            return self.objects, deregistered

        input_centroids = np.array(input_centroids, dtype="float")

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())

            # Usar posiciones PREDICHAS para la comparación
            predicted_centroids = np.array(
                [self._predict(oid) for oid in object_ids]
            )

            # Matriz de distancias euclidianas entre predicciones y detecciones
            D = dist.cdist(predicted_centroids, input_centroids)

            # Algoritmo Húngaro para asignación global óptima. Resuelve cruces de abejas.
            rows, cols = linear_sum_assignment(D)

            used_rows, used_cols = set(), set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue

                if D[row, col] > self.max_distance:
                    continue

                object_id = object_ids[row]
                old_pos = self.objects[object_id]
                new_pos = np.array(input_centroids[col], dtype="float")

                # Actualizar velocidad
                new_velocity = new_pos - old_pos
                self.velocities[object_id] = (
                    self.velocities[object_id] * 0.5 + new_velocity * 0.5
                )

                # Suavizado adaptativo según velocidad
                smoothed = self._adaptive_smooth(
                    old_pos, new_pos, self.velocities[object_id]
                )
                self.objects[object_id] = smoothed
                self.disappeared[object_id] = 0

                # Guardar snapshot activo (posicion/velocidad reales, sin amortiguar)
                self.last_active_pos[object_id] = smoothed.copy()
                self.last_active_vel[object_id] = self.velocities[object_id].copy()

                # Guardar punto en la trayectoria (limitar longitud)
                trail = self.trajectories[object_id]
                trail.append(tuple(smoothed.astype(int)))
                if len(trail) > self.max_trail:
                    self.trajectories[object_id] = trail[-self.max_trail:]

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                # Avanzar posición según velocidad, pero frenar fuertemente
                self.objects[object_id] = self._predict(object_id)
                self.velocities[object_id] *= 0.4
                if self.disappeared[object_id] > self.max_disappeared:
                    last_pos, last_vel, hist_len = self.deregister(object_id)
                    deregistered.append((object_id, last_pos, last_vel, hist_len))

            unused_cols = set(range(0, D.shape[1])).difference(used_cols)
            for col in unused_cols:
                self.register(input_centroids[col])

        return self.objects, deregistered