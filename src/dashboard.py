"""
dashboard.py — Servidor web liviano para monitoreo remoto en tiempo real.

Expone:
  GET /           -> Página HTML con contadores actualizados via SSE
  GET /api/status -> JSON con el estado actual del pipeline
  GET /stream     -> Server-Sent Events (SSE) con actualizaciones en vivo

Uso:
    from src.dashboard import Dashboard
    dash = Dashboard()
    dash.start()               # lanza Flask en thread background (no bloquea)
    dash.update(in_count=5, out_count=3, total=12, frame=450, fps_proc=4.2)
"""

import json
import threading
from queue import Queue, Empty

try:
    from flask import Flask, Response, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Estado compartido (thread-safe con lock)
# ---------------------------------------------------------------------------

class _State:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "in": 0,
            "out": 0,
            "total": 0,
            "frame": 0,
            "fps_proc": 0.0,
            "running": True,
        }
        self._subscribers: list = []

    def update(self, **kwargs):
        with self._lock:
            self._data.update(kwargs)
            snapshot = dict(self._data)
        for q in list(self._subscribers):
            try:
                q.put_nowait(snapshot)
            except Exception:
                pass

    def get(self):
        with self._lock:
            return dict(self._data)

    def subscribe(self):
        q = Queue(maxsize=10)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not q]


_state = _State()


# ---------------------------------------------------------------------------
# HTML del dashboard
# ---------------------------------------------------------------------------

_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tetragonisca Vision - Dashboard</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:      #0a0f1e;
      --surface: #111827;
      --border:  #1f2937;
      --accent:  #f59e0b;
      --green:   #10b981;
      --red:     #ef4444;
      --blue:    #3b82f6;
      --text:    #f1f5f9;
      --muted:   #6b7280;
    }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem;
    }
    header { text-align: center; margin-bottom: 2.5rem; }
    header h1 { font-size: 1.6rem; font-weight: 700; letter-spacing: -0.5px; }
    header h1 span { color: var(--accent); }
    header p { color: var(--muted); font-size: 0.85rem; margin-top: 0.4rem; }
    .dot {
      display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: var(--green);
      margin-right: 6px; animation: pulse 1.5s infinite;
    }
    .dot.offline { background: var(--red); animation: none; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.2rem; width: 100%; max-width: 860px;
    }
    .card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 16px; padding: 1.8rem 1.5rem;
      display: flex; flex-direction: column; gap: 0.5rem;
      transition: transform .2s, border-color .2s;
    }
    .card:hover { transform: translateY(-3px); border-color: #374151; }
    .label { font-size:.78rem; font-weight:600; text-transform:uppercase; letter-spacing:1px; color:var(--muted); }
    .value { font-size:3rem; font-weight:900; line-height:1; transition:color .3s; }
    .sub   { font-size:.8rem; color:var(--muted); }
    .green  .value { color: var(--green); }
    .red    .value { color: var(--red); }
    .blue   .value { color: var(--blue); }
    .yellow .value { color: var(--accent); }
    #ts { margin-top:2rem; font-size:.78rem; color:var(--muted); text-align:center; }
    footer { margin-top:2rem; color:var(--muted); font-size:.78rem; }
  </style>
</head>
<body>
  <header>
    <h1>&#x1F41D; <span>Tetragonisca</span> Vision EdgeAI</h1>
    <p><span class="dot" id="dot"></span><span id="stxt">Conectando&hellip;</span></p>
  </header>
  <div class="grid">
    <div class="card green">
      <span class="label">Entradas (IN)</span>
      <span class="value" id="v-in">&mdash;</span>
      <span class="sub">Abejas que ingresaron</span>
    </div>
    <div class="card red">
      <span class="label">Salidas (OUT)</span>
      <span class="value" id="v-out">&mdash;</span>
      <span class="sub">Abejas que salieron</span>
    </div>
    <div class="card yellow">
      <span class="label">Total detectadas</span>
      <span class="value" id="v-total">&mdash;</span>
      <span class="sub">IDs asignados desde inicio</span>
    </div>
    <div class="card blue">
      <span class="label">Frame actual</span>
      <span class="value" id="v-frame">&mdash;</span>
      <span class="sub" id="v-fps">&mdash; FPS procesados</span>
    </div>
  </div>
  <div id="ts">Ultima actualizacion: &mdash;</div>
  <footer>Tetragonisca Vision EdgeAI &middot; Pi Zero 2W</footer>

  <script>
    const $ = id => document.getElementById(id);
    function update(d) {
      $('v-in').textContent    = d['in']    ?? '-';
      $('v-out').textContent   = d['out']   ?? '-';
      $('v-total').textContent = d['total'] ?? '-';
      $('v-frame').textContent = d['frame'] ?? '-';
      $('v-fps').textContent   = (d['fps_proc']??0).toFixed(1) + ' FPS procesados';
      $('dot').classList.remove('offline');
      $('stxt').textContent = 'En vivo';
      $('ts').textContent = 'Ultima actualizacion: ' + new Date().toLocaleTimeString();
    }
    function connect() {
      const es = new EventSource('/stream');
      es.onmessage = e => { try { update(JSON.parse(e.data)); } catch(_){} };
      es.onerror   = () => {
        $('dot').classList.add('offline');
        $('stxt').textContent = 'Sin conexion, reintentando...';
        es.close();
        setTimeout(connect, 3000);
      };
    }
    connect();
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------

def _create_app():
    app = Flask(__name__)
    app.logger.disabled = True

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    @app.route('/')
    def index():
        return _HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route('/api/status')
    def api_status():
        return jsonify(_state.get())

    @app.route('/stream')
    def stream():
        q = _state.subscribe()

        def generate():
            try:
                yield f"data: {json.dumps(_state.get())}\n\n"
                while True:
                    try:
                        data = q.get(timeout=30)
                        yield f"data: {json.dumps(data)}\n\n"
                    except Empty:
                        yield ": heartbeat\n\n"
            finally:
                _state.unsubscribe(q)

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )

    return app


# ---------------------------------------------------------------------------
# Clase pública
# ---------------------------------------------------------------------------

class Dashboard:
    """
    Dashboard web liviano. Corre Flask en un thread daemon de fondo.

    Ejemplo:
        dash = Dashboard(port=5000)
        dash.start()
        # Por cada frame procesado:
        dash.update(in_count=5, out_count=3, total=12, frame=450, fps_proc=4.2)
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        if not FLASK_AVAILABLE:
            raise ImportError(
                "Flask no instalado. Ejecuta: pip install flask"
            )
        self.host = host
        self.port = port
        self._app = _create_app()

    def start(self):
        """Lanza el servidor en un thread daemon (no bloquea el pipeline)."""
        t = threading.Thread(
            target=self._app.run,
            kwargs={"host": self.host, "port": self.port, "threaded": True},
            daemon=True,
            name="dashboard-flask",
        )
        t.start()
        print(f"[Dashboard] http://{self.host}:{self.port}  (accede desde la red local)")

    def update(
        self,
        in_count: int = 0,
        out_count: int = 0,
        total: int = 0,
        frame: int = 0,
        fps_proc: float = 0.0,
    ):
        """Actualiza el estado y notifica a todos los clientes SSE conectados."""
        _state.update(**{
            "in": in_count, "out": out_count,
            "total": total, "frame": frame, "fps_proc": fps_proc,
        })
