"""
Genera detecciones FOMO cacheadas para varios escenarios que simulan
las condiciones de captura (video directo vs. webcam apuntando a un monitor).

Guarda por escenario un .npz con:
  grids  : salida cruda de FOMO por frame de cámara  [N, gh, gw] (prob clase Abeja, float16)
  times  : timestamp (s) de cada frame de cámara
  size   : (w, h) del frame
  roi    : (cx, cy, r) equivalente en coordenadas del frame
  box    : (x0, y0, w, h) región del frame que vio FOMO
Uso: python bench/make_scenarios.py --video examples/videos/0040-1.mp4 --out bench/cache/
(~5 min en PC; requiere ai-edge-litert)
"""
import argparse, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        import tensorflow as _tf   # Windows: no hay ruedas de LiteRT
        tflite = _tf.lite
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        import tensorflow as _tf   # Windows/PC
        tflite = _tf.lite

ROI_1080 = (900, 600, 220)


class RawFomo:
    def __init__(self, model):
        self.it = tflite.Interpreter(model_path=model, num_threads=4)
        self.it.allocate_tensors()
        self.inp = self.it.get_input_details()[0]
        self.out = self.it.get_output_details()[0]
        self.h, self.w = self.inp['shape'][1], self.inp['shape'][2]

    def grid(self, frame):
        rgb = cv2.cvtColor(cv2.resize(frame, (self.w, self.h)), cv2.COLOR_BGR2RGB)
        x = (rgb.astype(np.int32) - 128).astype(np.int8)[None]
        self.it.set_tensor(self.inp['index'], x)
        self.it.invoke()
        o = self.it.get_tensor(self.out['index'])[0]
        o = o[..., 1] if o.shape[-1] > 1 else o[..., 0]
        return ((o.astype(np.float32) + 128) / 256.0).astype(np.float16)


def webcam_view(src, rng, s, off, H):
    """Simula el monitor filmado por la webcam 640x480."""
    h, w = src.shape[:2]
    small = cv2.resize(src, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    canvas = np.full((480, 640, 3), 18, np.uint8)        # marco oscuro del monitor
    sh, sw = small.shape[:2]
    canvas[off[1]:off[1] + sh, off[0]:off[0] + sw] = small
    canvas = cv2.warpPerspective(canvas, H, (640, 480), borderValue=(18, 18, 18))
    f = canvas.astype(np.float32)
    f = (f - 128) * 0.85 + 128 + 8                       # menos contraste / brillo de pantalla
    f = cv2.GaussianBlur(f, (0, 0), 0.9)                 # desenfoque óptico
    f += rng.normal(0, 4, f.shape)                       # ruido de sensor
    f = np.clip(f, 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode('.jpg', f, [cv2.IMWRITE_JPEG_QUALITY, 70])  # MJPG
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', required=True)
    ap.add_argument('--model', default='models/fomo_tetragonisca_int8.lite')
    ap.add_argument('--out', default='cache')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    det = RawFomo(a.model)

    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Webcam: monitor ocupa ~94% del ancho, leve keystone
    s = 600 / 1920
    off = (20, 71)
    src_pts = np.float32([[0, 0], [640, 0], [640, 480], [0, 480]])
    dst_pts = np.float32([[6, 4], [634, 10], [628, 474], [10, 478]])
    H = cv2.getPerspectiveTransform(src_pts, dst_pts)
    cx, cy, r = ROI_1080
    p = cv2.perspectiveTransform(np.float32([[[cx * s + off[0], cy * s + off[1]]]]), H)[0, 0]
    roi_cam = (float(p[0]), float(p[1]), r * s)

    # (nombre, fps de cámara, frames promediados por exposición)
    cams = [('webcam', 30, 2), ('webcam_dark', 15, 4)]
    step = {nm: int(round(fps / cf)) for nm, cf, _ in cams}
    acc = {nm: {'grids': [], 'times': [], 'rng': np.random.default_rng(0)} for nm, _, _ in cams}
    orig_grids = []

    buf = []   # últimos frames para la exposición
    k = 0
    while True:
        ret, f = cap.read()
        if not ret:
            break
        orig_grids.append(det.grid(f))
        buf.append(f.astype(np.float32))
        buf = buf[-4:]
        for nm, cf, blend in cams:
            # el frame de cámara que empieza en k-blend+1 se completa ahora
            start = k - blend + 1
            if start >= 0 and start % step[nm] == 0:
                src = np.mean(buf[-blend:], axis=0).astype(np.uint8)
                cam = webcam_view(src, acc[nm]['rng'], s, off, H)
                acc[nm]['grids'].append(det.grid(cam))
                acc[nm]['times'].append(start / fps)
                if start == 1200:
                    cv2.imwrite(os.path.join(a.out, f'{nm}_sample.jpg'), cam)
        k += 1
    print(f'{k} frames @ {fps:.2f} fps')
    np.savez_compressed(os.path.join(a.out, 'orig.npz'), grids=np.stack(orig_grids),
                        times=np.arange(k) / fps, size=(1920, 1080), roi=ROI_1080, box=(0, 0, 1920, 1080))
    for nm, _, _ in cams:
        np.savez_compressed(os.path.join(a.out, f'{nm}.npz'), grids=np.stack(acc[nm]['grids']),
                            times=np.array(acc[nm]['times']), size=(640, 480), roi=roi_cam, box=(0, 0, 640, 480))
        print(nm, len(acc[nm]['grids']), 'frames, roi', roi_cam)


if __name__ == '__main__':
    main()
