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


# =============================================================================
# Contador v2: origen-destino + cruce directo con histéresis
# =============================================================================

class BeeCounterV2:
    """
    Cuenta entradas/salidas usando el recorrido completo de cada track,
    no solo los dos últimos puntos.

    Regla origen-destino:
      - OUT: el track nació DENTRO de la ROI y terminó FUERA.
      - IN : el track nació FUERA de la ROI y terminó DENTRO.
      - Nació y terminó del mismo lado (guardianas, abejas que revolotean): no cuenta.

    Se evalúa en dos momentos:
      1. En vivo: cuando un track confirmado sale de la banda de histéresis
         hacia el lado opuesto a su origen, se cuenta al instante (HUD en tiempo real).
      2. Al cerrarse el track: si no se contó en vivo, su última posición se
         proyecta con la velocidad del Kalman durante `lookahead_s`. Cubre las
         abejas que despegan y FOMO deja de ver (desenfoque) antes del borde.
         Con `back_project=True` se hace lo simétrico con el nacimiento
         (abejas que aterrizan y FOMO solo detecta ya dentro de la ROI).

    Cada track cuenta como máximo una vez. Distancias en fracciones del radio
    y velocidades en radios/s: no depende de la resolución ni de los FPS.
    """

    def __init__(self, roi_center, roi_radius, hysteresis=0.15, lookahead_s=0.25,
                 min_speed=1.5, back_project=True):
        """
        hysteresis:   banda alrededor del borde para el conteo en vivo.
                      Dentro = d < r(1-h); Fuera = d > r(1+h).
        lookahead_s:  segundos que se proyecta un track al cerrarse.
        min_speed:    velocidad mínima (radios/s) para confiar en la proyección.
        back_project: proyectar también hacia atrás el nacimiento del track.
        """
        self.c = np.array(roi_center, dtype=float)
        self.r = float(roi_radius)
        self.r_in = self.r * (1 - hysteresis)
        self.r_out = self.r * (1 + hysteresis)
        self.lookahead_s = lookahead_s
        self.min_speed = min_speed * self.r
        self.back_project = back_project
        self.in_count = 0
        self.out_count = 0
        self.counted = set()   # IDs contados (compatibilidad con v1)
        self.events = []       # (t, "in"/"out", track_id, x, y)

    def _d(self, p):
        return float(np.linalg.norm(np.asarray(p, dtype=float) - self.c))

    def _origin(self, tr):
        if self._d(tr.birth_pos) >= self.r:
            return "outside"
        v = tr.early_vel
        if self.back_project and v is not None and np.linalg.norm(v) >= self.min_speed:
            if self._d(tr.birth_pos - v * self.lookahead_s) >= self.r:
                return "outside"
        return "inside"

    def _destination(self, tr):
        end = tr.last_hit_pos
        if np.linalg.norm(tr.vel) >= self.min_speed:
            end = end + tr.vel * self.lookahead_s
        return "outside" if self._d(end) >= self.r else "inside"

    def _register(self, tr, kind):
        tr.counted = kind
        self.counted.add(tr.id)
        self.events.append((tr.t_last_hit, kind, tr.id, float(tr.last_hit_pos[0]), float(tr.last_hit_pos[1])))
        if kind == "in":
            self.in_count += 1
        else:
            self.out_count += 1

    def update(self, active_tracks, finished_tracks=()):
        # 1. Conteo en vivo al salir de la banda de histéresis
        for tr in active_tracks:
            if tr.counted:
                continue
            d = self._d(tr.last_hit_pos)
            if d > self.r_out and self._origin(tr) == "inside":
                self._register(tr, "out")
            elif d < self.r_in and self._origin(tr) == "outside":
                self._register(tr, "in")

        # 2. Tracks cerrados: origen-destino con proyección
        for tr in finished_tracks:
            if tr.counted:
                continue
            o, dst = self._origin(tr), self._destination(tr)
            if o == "inside" and dst == "outside":
                self._register(tr, "out")
            elif o == "outside" and dst == "inside":
                self._register(tr, "in")

        return {"in": self.in_count, "out": self.out_count}


class BeeCounterCross(BeeCounterV2):
    """
    Cuenta CADA cruce del borde de la ROI, no una vez por track.

    BeeCounterV2 cuenta como máximo un evento por track. Si un track se queda
    pegado a una guardiana y luego "salta" a la abeja que despega, la salida se
    pierde. Aquí cada track lleva su lado actual (dentro/fuera, con histéresis)
    y cada cambio de lado es un evento candidato:
      - dentro -> fuera: OUT;  fuera -> dentro: IN.
      - Si el cruce se revierte antes de `cancel_s` (abeja que se asoma y
        vuelve), se anulan los dos.
      - Un cruce se confirma al pasar `cancel_s` sin reversa o al cerrarse el track.
    El lado inicial y el destino final usan las mismas proyecciones que V2.
    No modifica `tr.counted`, así puede convivir con un BeeCounterV2 (ver BeeCounterHybrid).
    """

    def __init__(self, roi_center, roi_radius, cancel_s=0.5, **kw):
        super().__init__(roi_center, roi_radius, **kw)
        self.cancel_s = cancel_s
        self._side = {}      # track id -> "inside" / "outside"
        self._pending = {}   # track id -> (kind, t, x, y)

    def _emit(self, tr, kind, t, x, y):
        self.counted.add(tr.id)
        self.events.append((t, kind, tr.id, x, y))
        if kind == "in":
            self.in_count += 1
        else:
            self.out_count += 1

    def _transition(self, tr, new_side, t, pos):
        kind = "out" if new_side == "outside" else "in"
        self._side[tr.id] = new_side
        pend = self._pending.pop(tr.id, None)
        if pend is not None:
            if pend[0] != kind and t - pend[1] < self.cancel_s:
                return                     # se asomó y volvió: se anulan ambos
            self._emit(tr, *pend)
        self._pending[tr.id] = (kind, t, float(pos[0]), float(pos[1]))

    def update(self, active_tracks, finished_tracks=()):
        for tr in active_tracks:
            if tr.id not in self._side:
                self._side[tr.id] = self._origin(tr)
            d = self._d(tr.last_hit_pos)
            side = "inside" if d < self.r_in else "outside" if d > self.r_out else None
            if side is not None and side != self._side[tr.id]:
                self._transition(tr, side, tr.t_last_hit, tr.last_hit_pos)
            pend = self._pending.get(tr.id)
            if pend is not None and tr.t_last_hit - pend[1] >= self.cancel_s:
                self._emit(tr, *self._pending.pop(tr.id))

        for tr in finished_tracks:
            if tr.id not in self._side:
                self._side[tr.id] = self._origin(tr)
            dst = self._destination(tr)
            if dst != self._side[tr.id]:
                self._transition(tr, dst, tr.t_last_hit, tr.last_hit_pos)
            pend = self._pending.pop(tr.id, None)
            if pend is not None:
                self._emit(tr, *pend)
            self._side.pop(tr.id, None)

        return {"in": self.in_count, "out": self.out_count}


class BeeCounterHybrid:
    """
    Salidas por cruces (BeeCounterCross) y entradas por origen-destino (BeeCounterV2).

    Las salidas se perdían cuando un track largo (guardiana) absorbía a la abeja
    que despega: contar cada cruce hacia fuera las recupera. Para las entradas,
    contar cada cruce suma falsas entradas de guardianas que caminan por el
    borde, así que se mantiene la regla de una entrada por track, sin proyectar
    hacia atrás el nacimiento (`in_back_project=False`), que también las reducía.
    Expone la misma interfaz que BeeCounterV2 (update, events, in_count, out_count).
    """

    def __init__(self, roi_center, roi_radius, cancel_s=0.5, in_back_project=False, **kw):
        self._in = BeeCounterV2(roi_center, roi_radius, back_project=in_back_project, **kw)
        self._out = BeeCounterCross(roi_center, roi_radius, cancel_s=cancel_s, **kw)
        self.events = []
        self.counted = set()
        self.in_count = 0
        self.out_count = 0

    def update(self, active_tracks, finished_tracks=()):
        n_in, n_out = len(self._in.events), len(self._out.events)
        self._in.update(active_tracks, finished_tracks)
        self._out.update(active_tracks, finished_tracks)
        new = [e for e in self._in.events[n_in:] if e[1] == "in"]
        new += [e for e in self._out.events[n_out:] if e[1] == "out"]
        for e in sorted(new):
            self.events.append(e)
            self.counted.add(e[2])
            if e[1] == "in":
                self.in_count += 1
            else:
                self.out_count += 1
        return {"in": self.in_count, "out": self.out_count}
