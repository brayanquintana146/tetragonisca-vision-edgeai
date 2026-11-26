"""
Mide cuántas imágenes por segundo entrega de verdad una webcam en Windows, a 1280x720 y a 1920x1080.

Sirve para elegir --cam-width, --cam-height y --cam-fps antes de contar con --video 0:
una cámara puede aceptar 60 fps y entregar menos con poca luz o sin formato MJPG.

Uso: python tools/probar_cam.py [índice de la cámara, 0 por defecto]
"""
import cv2, time, sys
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for w, h in [(1280, 720), (1920, 1080)]:
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    n, t0 = 0, time.time()
    while time.time() - t0 < 5:
        ok, _ = cap.read()
        n += ok
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little").decode()
    print(f"{w}x{h}: {n/5:.1f} fps reales | formato {fourcc} | autofoco {cap.get(cv2.CAP_PROP_AUTOFOCUS)}")
    cap.release()
