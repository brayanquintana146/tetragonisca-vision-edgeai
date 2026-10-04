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


# =============================================================================
# Tracker v2: Kalman de velocidad constante + Húngaro con gating
# =============================================================================

class Track:
    """Estado de una abeja rastreada."""

    __slots__ = ("id", "x", "P", "confirmed", "n_hits", "t_first", "t_last_hit",
                 "birth_pos", "last_hit_pos", "hits", "misses", "counted", "early_vel")

    def __init__(self, tid, pos, t, P0):
        self.id = tid
        self.x = np.array([pos[0], pos[1], 0.0, 0.0])   # [x, y, vx, vy] (px, px/s)
        self.P = P0.copy()
        self.confirmed = False
        self.n_hits = 1
        self.t_first = t
        self.t_last_hit = t
        self.birth_pos = np.array(pos[:2], dtype=float)
        self.last_hit_pos = np.array(pos[:2], dtype=float)
        self.hits = [(t, float(pos[0]), float(pos[1]))]   # detecciones reales asociadas
        self.misses = 0
        self.counted = None      # None | "in" | "out" (lo escribe el contador)
        self.early_vel = None    # velocidad estimada al confirmarse (px/s)

    @property
    def pos(self):
        return self.x[:2]

    @property
    def vel(self):
        return self.x[2:]


class BeeTracker:
    """
    Rastreador multi-abeja independiente de la resolución y de los FPS.

    Diferencias con EuTrack:
    - Usa el tiempo real entre frames (dt en segundos): funciona igual a 60 fps
      que a 8 fps o con frames perdidos por la webcam.
    - Todas las distancias se expresan en múltiplos de `scale` (el radio de la
      ROI en px), así que los mismos parámetros sirven en 1920x1080 y en 640x480.
    - Filtro de Kalman de velocidad constante: predice sin el retraso del
      suavizado exponencial y su incertidumbre crece mientras la abeja no se ve.
    - Gating ANTES del Algoritmo Húngaro: pares imposibles nunca compiten.
    - Tracks tentativos: una detección aislada (reflejo, ruido del monitor) no
      crea un ID definitivo hasta confirmarse con `min_hits` detecciones.
    - Doble umbral (estilo ByteTrack): detecciones débiles (blur) pueden
      continuar un track existente, pero solo las fuertes crean tracks nuevos.
    """

    def __init__(self, scale, accel_std=40.0, meas_std=0.08, init_vel_std=4.0,
                 gate_sigma=3.0, min_gate=0.35, max_gate=1.2,
                 max_lost_s=0.6, tentative_lost_s=0.1, min_hits=2,
                 birth_min_prob=0.55, max_hits_kept=60, max_gate_tentative=None):
        """
        scale:            px que equivalen a 1 unidad (radio de la ROI).
        accel_std:        aceleración típica de una abeja (unidades/s²). Alto = reacciona rápido.
        meas_std:         error de posición de FOMO (unidades). La grilla 40x40 da ~0.08.
        init_vel_std:     incertidumbre de velocidad de un track recién nacido (unidades/s).
        gate_sigma:       ventana de asociación en desviaciones estándar de la predicción.
        min_gate/max_gate: límites de esa ventana (unidades).
        max_lost_s:       segundos sin detección antes de cerrar un track confirmado.
        tentative_lost_s: ídem para tracks tentativos.
        min_hits:         detecciones necesarias para confirmar un track.
        birth_min_prob:   confianza mínima para crear un track nuevo.
        max_gate_tentative: max_gate para tracks tentativos (None = igual a max_gate). Permite
                          un max_gate chico para los confirmados (no saltan entre abejas
                          vecinas) sin dejar de enlazar abejas en vuelo rápido.
        """
        s = float(scale)
        self.scale = s
        self.q = accel_std * s
        self.r = meas_std * s
        self.P0 = np.diag([self.r ** 2, self.r ** 2, (init_vel_std * s) ** 2, (init_vel_std * s) ** 2])
        self.R = np.eye(2) * self.r ** 2
        self.H = np.array([[1.0, 0, 0, 0], [0, 1.0, 0, 0]])
        self.gate_sigma = gate_sigma
        self.min_gate = min_gate * s
        self.max_gate = max_gate * s
        self.max_gate_tentative = self.max_gate if max_gate_tentative is None else max_gate_tentative * s
        self.max_lost_s = max_lost_s
        self.tentative_lost_s = tentative_lost_s
        self.min_hits = min_hits
        self.birth_min_prob = birth_min_prob
        self.max_hits_kept = max_hits_kept

        self.tracks = OrderedDict()   # {id: Track}
        self.next_id = 0              # IDs internos (incluye tentativos)
        self.confirmed_total = 0      # abejas únicas confirmadas
        self._next_public_id = 0
        self.t_prev = None

    # ------------------------------------------------------------------ Kalman
    def _F_Q(self, dt):
        F = np.eye(4)
        F[0, 2] = F[1, 3] = dt
        q2 = self.q ** 2
        dt2, dt3, dt4 = dt * dt, dt ** 3, dt ** 4
        Q = q2 * np.array([[dt4 / 4, 0, dt3 / 2, 0],
                           [0, dt4 / 4, 0, dt3 / 2],
                           [dt3 / 2, 0, dt2, 0],
                           [0, dt3 / 2, 0, dt2]])
        return F, Q

    def _predict(self, tr, F, Q):
        tr.x = F @ tr.x
        tr.P = F @ tr.P @ F.T + Q

    def _correct(self, tr, z):
        y = z - self.H @ tr.x
        S = self.H @ tr.P @ self.H.T + self.R
        K = tr.P @ self.H.T @ np.linalg.inv(S)
        tr.x = tr.x + K @ y
        tr.P = (np.eye(4) - K @ self.H) @ tr.P

    def _gate(self, tr):
        S = tr.P[:2, :2] + self.R
        sigma = np.sqrt(np.max(np.linalg.eigvalsh(S)))
        hi = self.max_gate if tr.confirmed else self.max_gate_tentative
        return float(np.clip(self.gate_sigma * sigma, self.min_gate, hi))

    # ------------------------------------------------------------------ API
    def update(self, detections, t):
        """
        detections: lista de (cx, cy) o (cx, cy, prob) en px.
        t:          timestamp del frame en segundos (tiempo de captura).
        Devuelve (tracks_confirmados_activos, tracks_confirmados_terminados).
        """
        dt = 0.0 if self.t_prev is None else max(1e-3, t - self.t_prev)
        self.t_prev = t
        dets = [(float(d[0]), float(d[1]), float(d[2]) if len(d) > 2 else 1.0) for d in detections]

        # 1. Predicción
        F, Q = self._F_Q(dt)
        tids = list(self.tracks.keys())
        for tid in tids:
            self._predict(self.tracks[tid], F, Q)

        # 2. Asociación global con gating previo
        matched_t, matched_d = set(), set()
        if tids and dets:
            pred = np.array([self.tracks[tid].pos for tid in tids])
            Z = np.array([d[:2] for d in dets])
            D = dist.cdist(pred, Z)
            BIG = 1e9
            C = D.copy()
            for i, tid in enumerate(tids):
                tr = self.tracks[tid]
                C[i, D[i] > self._gate(tr)] = BIG
                if not tr.confirmed:
                    C[i] += 0.1 * self.scale   # los confirmados tienen prioridad
            rows, cols = linear_sum_assignment(C)
            for r_, c_ in zip(rows, cols):
                if C[r_, c_] >= BIG:
                    continue
                tr = self.tracks[tids[r_]]
                z = Z[c_]
                self._correct(tr, z)
                tr.n_hits += 1
                tr.misses = 0
                tr.t_last_hit = t
                tr.last_hit_pos = z.copy()
                tr.hits.append((t, float(z[0]), float(z[1])))
                if len(tr.hits) > self.max_hits_kept:
                    del tr.hits[0]
                if tr.early_vel is None and tr.n_hits >= 3:
                    tr.early_vel = tr.vel.copy()
                if not tr.confirmed and tr.n_hits >= self.min_hits:
                    tr.confirmed = True
                    self.confirmed_total += 1
                matched_t.add(tids[r_])
                matched_d.add(c_)

        # 3. Tracks sin detección: envejecen y se cierran por tiempo
        finished = []
        for tid in tids:
            if tid in matched_t:
                continue
            tr = self.tracks[tid]
            tr.misses += 1
            limit = self.max_lost_s if tr.confirmed else self.tentative_lost_s
            if t - tr.t_last_hit > limit:
                del self.tracks[tid]
                if tr.confirmed:
                    finished.append(tr)

        # 4. Detecciones fuertes sin asignar: tracks tentativos nuevos
        for j, d in enumerate(dets):
            if j in matched_d or d[2] < self.birth_min_prob:
                continue
            self.tracks[self.next_id] = Track(self.next_id, d, t, self.P0)
            self.next_id += 1

        active = [tr for tr in self.tracks.values() if tr.confirmed]
        return active, finished

    def flush(self):
        """Cierra todos los tracks (fin del video). Devuelve los confirmados."""
        done = [tr for tr in self.tracks.values() if tr.confirmed]
        self.tracks.clear()
        return done

    # Compatibilidad con el dibujado de main.py
    @property
    def trajectories(self):
        return OrderedDict((tr.id, [(int(x), int(y)) for _, x, y in tr.hits])
                           for tr in self.tracks.values() if tr.confirmed)
