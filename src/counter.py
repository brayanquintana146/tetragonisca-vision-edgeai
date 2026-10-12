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
      - Si el cruce se revierte antes de `cancel_s` (abeja que se asoma o guardiana
        que camina por el borde y vuelve), se anulan los dos.
      - Un cruce se confirma al pasar `cancel_s` sin reversa o al cerrarse el track.
    El lado inicial y el destino final usan las mismas proyecciones que V2.
    No modifica `tr.counted`, así puede convivir con un BeeCounterV2 (ver BeeCounterHybrid).
    """

    def __init__(self, roi_center, roi_radius, cancel_s=0.5, proj_min_speed=1.5, **kw):
        super().__init__(roi_center, roi_radius, **kw)
        self.cancel_s = cancel_s
        # Proyección al cerrarse el track: solo si va a más de proj_min_speed (radios/s).
        # Subirlo evita "proyectar" fuera de la ROI abejas casi quietas cuya velocidad del
        # Kalman tiembla (salidas falsas), a cambio de perder algunas salidas reales
        self.proj_min_speed = proj_min_speed * self.r
        self._side = {}      # track id -> "inside" / "outside"
        self._pending = {}   # track id -> (kind, t, x, y)

    def _destination(self, tr):
        end = tr.last_hit_pos
        if np.linalg.norm(tr.vel) >= self.proj_min_speed:
            end = end + tr.vel * self.lookahead_s
        return "outside" if self._d(end) >= self.r else "inside"

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

    Con `flash_exits=True` suma las salidas de FlashExits (abejas que despegan y FOMO
    solo ve 1-3 frames) y deja de proyectar fuera de la ROI los tracks que se cierran:
    esa proyección daba la mayoría de las salidas falsas. Hay que pasarle a update()
    las detecciones del frame y su tiempo, y llamar update(..., final=True) al terminar.

    Con `core` (fracción del radio, p. ej. 0.5) una salida solo cuenta si la abeja pasó por
    el centro de la ROI (la boca de la piquera) desde su salida anterior, y una entrada
    solo si la abeja llega a ese centro. Así no cuentan las guardianas que vuelan frente
    a la piquera y cruzan el borde del círculo sin llegar a la boca.

    Con `static_s` (segundos, p. ej. 2.0; necesita las detecciones, o sea `flash_exits`) se
    descarta una salida cuyo punto ya tenía una detección (a menos de `static_near` escalas)
    entre `static_s` y `static_gap` segundos antes. Una abeja que se va no sale de un sitio
    donde ya había algo: ese punto es una sombra o una abeja quieta que FOMO ve a ratos, y el
    tracker salta hacia ella cuando pierde a una abeja de la boca.

    Con `in_max_age` (segundos, p. ej. 3) una entrada solo cuenta si el track nació hace ese tiempo
    o menos: la abeja que entra lo hace enseguida, y un track viejo que "entra" suele ser una
    guardiana o un punto del fondo. Con `in_park_s` (p. ej. 0.15) tampoco cuenta si el track estuvo
    quieto fuera de la ROI (a menos de `park_near` escalas) ese tiempo o más justo antes de entrar:
    es un punto fijo del fondo que salta a una abeja que aparece en la piquera.

    Con `rep_s` (segundos, p. ej. 60; necesita `flash_exits`) una salida fugaz no cuenta si sale de
    un punto fijo repetido: un sitio del fondo que FOMO confunde con una abeja y que se enciende
    una y otra vez sin moverse, con más de `static_s` entre una vez y otra (ver FlashExits).
    """

    def __init__(self, roi_center, roi_radius, cancel_s=0.5, proj_min_speed=1.5, in_back_project=False,
                 flash_exits=False, track_scale=None, core=None, static_s=None, static_gap=0.1,
                 static_near=0.1, rep_s=None, rep_k=2, in_max_age=None, in_park_s=None, park_near=0.15, **kw):
        self._in = BeeCounterV2(roi_center, roi_radius, back_project=in_back_project, **kw)
        self._out = BeeCounterCross(roi_center, roi_radius, cancel_s=cancel_s,
                                    proj_min_speed=float("inf") if flash_exits else proj_min_speed, **kw)
        self._flash = FlashExits(roi_center, roi_radius, scale=track_scale,
                                 rep_s=rep_s, rep_k=rep_k) if flash_exits else None
        self._c = np.array(roi_center, dtype=float)
        self._in_max_age = in_max_age
        self._in_park_s = in_park_s
        self._park_near = park_near * float(roi_radius if track_scale is None else track_scale)
        self._r = float(roi_radius)
        self._core = None if not core else core * float(roi_radius)
        self._core_t = {}      # track id -> tiempos en que estuvo dentro del centro
        self._last_out = {}    # track id -> tiempo de su última salida aceptada
        self._in_wait = {}     # track id -> entrada esperando que la abeja llegue al centro
        self._static_s, self._static_gap = static_s, static_gap
        self._static_near = static_near * float(roi_radius if track_scale is None else track_scale)
        self._hist = []        # (t, detecciones) recientes, para static_s
        self.events = []
        self.counted = set()
        self.in_count = 0
        self.out_count = 0

    def update(self, active_tracks, finished_tracks=(), detections=None, t=None, final=False, parked=None):
        n_in, n_out = len(self._in.events), len(self._out.events)
        self._in.update(active_tracks, finished_tracks)
        self._out.update(active_tracks, finished_tracks)
        new = [e for e in self._in.events[n_in:] if e[1] == "in"]
        if (self._in_max_age is not None or self._in_park_s is not None) and new:
            by_id = {tr.id: tr for tr in list(active_tracks) + list(finished_tracks)}
            if self._in_max_age is not None:
                new = [e for e in new if e[2] not in by_id or e[0] - by_id[e[2]].t_first <= self._in_max_age]
            if self._in_park_s is not None:
                new = [e for e in new if e[2] not in by_id or self._parked_s(by_id[e[2]], e[0]) < self._in_park_s]
        new += [e for e in self._out.events[n_out:] if e[1] == "out"]
        if self._core is not None:
            new = self._gate_core(new, active_tracks, finished_tracks, final)
        if self._flash is not None:
            if detections is not None:
                self._flash.observe(detections, active_tracks, t, parked)
            new += self._flash.collect(self._out.events, t, final=final)
        if self._static_s and detections is not None:
            new = [e for e in new if e[1] != "out" or not self._static(e)]
            self._hist.append((t, [(float(d[0]), float(d[1])) for d in detections]))
            # las salidas fugaces se deciden hasta ~2 s tarde: guardar ventana de sobra
            self._hist = [h for h in self._hist if t - h[0] <= self._static_s + 3.0]
        for e in sorted(new):
            self.events.append(e)
            self.counted.add(e[2])
            if e[1] == "in":
                self.in_count += 1
            else:
                self.out_count += 1
        return {"in": self.in_count, "out": self.out_count}

    def _parked_s(self, tr, te):
        """Segundos que el track estuvo quieto fuera de la ROI justo antes de entrar."""
        hits = [h for h in tr.hits if h[0] <= te + 1e-9]
        k = len(hits) - 1
        while k >= 0 and np.hypot(hits[k][1] - self._c[0], hits[k][2] - self._c[1]) < self._r:
            k -= 1
        if k < 0:
            return 0.0
        j = k
        while j > 0 and np.hypot(hits[j - 1][1] - hits[k][1], hits[j - 1][2] - hits[k][2]) < self._park_near:
            j -= 1
        return hits[k][0] - hits[j][0]

    def _static(self, e):
        te, x, y = e[0], e[3], e[4]
        return any(te - self._static_s <= th <= te - self._static_gap
                   and any(np.hypot(x - dx, y - dy) < self._static_near for dx, dy in dets)
                   for th, dets in self._hist)

    def _gate_core(self, new, active_tracks, finished_tracks, final):
        for tr in list(active_tracks) + list(finished_tracks):
            if np.linalg.norm(tr.last_hit_pos - self._c) < self._core:
                times = self._core_t.setdefault(tr.id, [])
                if not times or times[-1] != tr.t_last_hit:
                    times.append(tr.t_last_hit)
        keep = []
        for e in new:
            times = self._core_t.get(e[2], [])
            if e[1] == "out":
                prev = self._last_out.get(e[2], -1e9)
                if any(prev < tc <= e[0] for tc in times):
                    self._last_out[e[2]] = e[0]
                    keep.append(e)
            else:
                self._in_wait[e[2]] = e
        done = {tr.id for tr in finished_tracks}
        for tid, e in list(self._in_wait.items()):
            if any(tc >= e[0] - 0.5 for tc in self._core_t.get(tid, [])):
                keep.append(e)
                del self._in_wait[tid]
            elif tid in done or final:
                del self._in_wait[tid]
        for tid in done:
            self._core_t.pop(tid, None)
            self._last_out.pop(tid, None)
        return keep


class FlashExits:
    """
    Salidas de abejas que despegan tan rápido que FOMO solo las ve en 1-3 frames.

    Al despegar, la abeja sale borrosa: aparece como una mancha fuera de la piquera en
    uno o dos frames, a unos 250 px de distancia entre uno y otro. El tracker no crea un
    ID con eso (pide dos detecciones seguidas con confianza alta), así que esa salida
    se perdía. Aquí se buscan esas manchas:
      1. Detección fuera de la ROI (hasta `r_max - 1` escalas del tracker más allá del borde),
         que no está a menos de `near` escalas de una abeja rastreada en ese frame.
      2. Las detecciones así se enlazan en "trazos" (a lo sumo `max_gap_s` entre una y
         otra y `max_speed` escalas/s).
      3. Un trazo de `max_hits` detecciones o menos que no se acerca a la piquera es una
         salida, con el tiempo y la posición de su primera detección.
      4. No se usan las detecciones a menos de `recent_near` escalas de donde hubo una abeja
         rastreada FUERA de la ROI en los últimos `recent_s` segundos: es una abeja que ya
         andaba volando por ahí (p. ej. una guardiana que revolotea), no una que despega.
      5. Se descarta si el contador de cruces ya contó una salida a menos de `dedup_s`
         y `dedup_deg` grados (es la misma abeja). Por eso cada salida se decide
         `hold_s` segundos después, cuando el contador de cruces ya habló.
    Los valores se eligieron con el video 0040-1 a 60 fps: a otros FPS hay que revisar
    `max_hits` y `max_gap_s`.
    """

    def __init__(self, roi_center, roi_radius, scale=None, r_min=1.0, r_max=2.5, near=0.4, max_gap_s=0.04,
                 max_speed=84.0, max_hits=3, inward=0.1, dedup_s=0.4, dedup_deg=40.0, hold_s=1.5,
                 recent_s=0.5, recent_near=0.6, rep_s=None, rep_near=0.1, rep_k=2, rep_gap=0.1,
                 rep_w2=2, rep_self=True):
        """scale: px de la escala del tracker (--track-scale); por defecto el radio de la ROI.
        La zona de búsqueda va desde el borde de la ROI hasta (r_max - 1) escalas más afuera.

        rep_s: memoria (s) de los puntos fijos. Un punto del fondo que FOMO confunde con una abeja
        se enciende siempre en el mismo sitio, una y otra vez; una abeja que despega no repite el
        sitio ni se queda quieta. Cada trazo que no se movió de su sitio (a menos de `rep_near`
        escalas) deja una marca; si duró 2 frames o más vale `rep_w2` marcas. Una salida no cuenta
        si en su punto hay `rep_k` marcas o más de otros momentos (separadas más de `rep_gap` s)
        dentro de los últimos `rep_s` segundos, ni (con `rep_self`) si su propio trazo estuvo quieto
        2 frames o más. Se aprende del propio video, sin fotos del fondo."""
        self.c = np.array(roi_center, dtype=float)
        self.r = float(roi_radius)
        s = self.r if scale is None else float(scale)
        self.d_min = r_min * self.r
        self.d_max = self.r + (r_max - 1.0) * s
        self.near = near * s
        self.max_gap_s, self.max_speed, self.max_hits = max_gap_s, max_speed * s, max_hits
        self.recent_s, self.recent_near = recent_s, recent_near * s
        self._recent = []    # (t, x, y) de abejas rastreadas fuera de la ROI
        self.inward, self.dedup_s, self.dedup_deg, self.hold_s = inward, dedup_s, dedup_deg, hold_s
        self._open = []      # trazos abiertos: listas de (t, x, y, d)
        self._cand = []      # salidas candidatas (t, x, y), esperando hold_s
        self._done = []      # salidas aceptadas (t, x, y)
        self.rep_s, self.rep_near, self.rep_k, self.rep_gap = rep_s, rep_near * s, rep_k, rep_gap
        self.rep_w2, self.rep_self = rep_w2, rep_self
        self._spots = []     # (t, x, y, peso) de trazos que no se movieron de su sitio

    def _ang(self, x, y):
        return np.degrees(np.arctan2(y - self.c[1], x - self.c[0]))

    def is_fixed_spot(self, te, x, y):
        """¿Hay rep_k o más marcas de otros momentos en este punto dentro de la memoria?"""
        if not self.rep_s:
            return False
        n = sum(w for ts, sx, sy, w in self._spots
                if te - self.rep_s <= ts and abs(ts - te) > self.rep_gap
                and np.hypot(x - sx, y - sy) < self.rep_near)
        return n >= self.rep_k

    def _close(self, tl):
        if self.rep_s and all(np.hypot(p[1] - tl[0][1], p[2] - tl[0][2]) < self.rep_near for p in tl):
            # quieto varios frames seguidos: una abeja en vuelo no hace eso, vale como rep_w2 marcas
            quieto = len(tl) >= 2
            self._spots.append(tl[0][:3] + (self.rep_w2 if quieto else 1,))
            if quieto and self.rep_self:
                return
        if len(tl) > self.max_hits:
            return
        if len(tl) >= 2 and tl[-1][3] < tl[0][3] - self.inward:
            return           # se acerca a la piquera: es una abeja que llega
        self._cand.append(tl[0][:3])

    def _quiet(self, tl):
        return len(tl) >= 2 and all(np.hypot(p[1] - tl[0][1], p[2] - tl[0][2]) < self.rep_near for p in tl)

    def observe(self, detections, active_tracks, t, parked=None):
        """parked: ids de tracks estacionados (BeeTracker.is_parked), o None si no se usa. No son
        abejas volando: solo tapan su propio sitio, no los despegues que pasan cerca, y un trazo
        quieto tampoco se enlaza con una detección lejana."""
        local = parked is not None
        parked = parked or ()
        spots = [tr.last_hit_pos for tr in active_tracks if tr.id in parked]
        active_tracks = [tr for tr in active_tracks if tr.id not in parked]
        seen = [tr.last_hit_pos for tr in active_tracks if tr.t_last_hit == t]
        keep = []
        for tl in self._open:
            if t - tl[-1][0] > self.max_gap_s:
                self._close(tl)
            else:
                keep.append(tl)
        self._open = keep
        self._recent = [q for q in self._recent if t - q[0] <= self.recent_s]
        recent = list(self._recent)
        for tr in active_tracks:
            if tr.t_last_hit == t and np.linalg.norm(tr.last_hit_pos - self.c) > self.r:
                self._recent.append((t, float(tr.last_hit_pos[0]), float(tr.last_hit_pos[1])))
        for det in detections:
            x, y = float(det[0]), float(det[1])
            if any(np.hypot(x - px, y - py) < self.recent_near for _, px, py in recent):
                continue
            d = float(np.hypot(x - self.c[0], y - self.c[1])) / self.r
            if not self.d_min <= d * self.r <= self.d_max:
                continue
            if any(np.hypot(x - p[0], y - p[1]) < self.near for p in seen):
                continue
            if any(np.hypot(x - p[0], y - p[1]) < self.rep_near * 1.5 for p in spots):
                continue
            best = None
            for tl in self._open:
                dt = t - tl[-1][0]
                dd = float(np.hypot(x - tl[-1][1], y - tl[-1][2]))
                reach = self.rep_near if (local and self._quiet(tl)) else self.max_speed * dt
                if 0 < dt <= self.max_gap_s and dd <= reach and (best is None or dd < best[0]):
                    best = (dd, tl)
            if best is not None:
                best[1].append((t, x, y, d))
            else:
                self._open.append([(t, x, y, d)])

    def collect(self, out_events, t, final=False):
        """Devuelve los eventos (t, "out", -1, x, y) ya decididos."""
        if final:
            for tl in self._open:
                self._close(tl)
            self._open = []
        ready = [c for c in self._cand if final or (t is not None and t - c[0] >= self.hold_s)]
        self._cand = [c for c in self._cand if c not in ready]
        if self.rep_s and t is not None:
            self._spots = [q for q in self._spots if t - q[0] <= self.rep_s + self.hold_s + 1.0]
        new = []
        for tc, x, y in sorted(ready):
            if self.is_fixed_spot(tc, x, y):
                continue
            a = self._ang(x, y)
            prev = [(e[0], e[3], e[4]) for e in out_events if e[1] == "out"] + self._done
            if any(abs(te - tc) < self.dedup_s and abs((self._ang(px, py) - a + 180) % 360 - 180) < self.dedup_deg
                   for te, px, py in prev):
                continue
            self._done.append((tc, x, y))
            new.append((tc, "out", -1, x, y))
        return new
