"""
Herramienta de anotación manual de entradas/salidas REALES en la piquera.

Sirve para construir la verdad de campo evento por evento y medir el tracker
contra lo que realmente pasó (no solo contra un total).

QUÉ MARCAR (definición de evento, sin guardianas)
-------------------------------------------------
  IN  (tecla i): una abeja que llega de afuera y ENTRA a la colmena
                 (se mete por el tubo y desaparece dentro).
  OUT (tecla o): una abeja que sale de la colmena y SE VA
                 (despega y abandona la escena).
  NO marcar:     guardianas que revolotean o caminan en el borde del tubo,
                 abejas que se asoman y vuelven a entrar, abejas que dan
                 vueltas cerca de la piquera sin entrar.
  Momento:       marca en el instante en que la abeja cruza el círculo
                 amarillo (o donde desaparece, si se pierde antes).
  Posición:      antes de pulsar i/o, haz CLIC sobre la abeja. Así el
                 evento guarda dónde estaba y se puede emparejar mejor.

CONTROLES
---------
  espacio        reproducir / pausar
  d / →          avanzar 1 frame         a / ←   retroceder 1 frame
  l              avanzar 1 segundo       j       retroceder 1 segundo
  + / -          velocidad de reproducción (x0.125 ... x1)
  clic           seleccionar la posición de la abeja
  i / o          marcar ENTRADA / SALIDA en el frame actual
  z              deshacer la última marca
  s              guardar
  q / Esc        guardar y salir

El CSV se guarda automáticamente al salir y se RETOMA si ya existe, así que
puedes anotar el video por partes.

Uso:
  python tools/anotar_eventos.py --video examples/videos/0040-1.mp4 ^
      --roi-x 900 --roi-y 600 --roi-r 220 --out data/gt_0040-1.csv
"""
import argparse
import csv
import os

import cv2

# Códigos de flechas de cv2.waitKeyEx (Windows / Linux GTK)
KEY_LEFT = {2424832, 65361}
KEY_RIGHT = {2555904, 65363}
SPEEDS = [0.125, 0.25, 0.5, 1.0]
WIN = "Anotar eventos - piquera"


def load_events(path):
    events = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                events.append({"t_s": float(r["t_s"]), "evento": r["evento"],
                               "frame": int(r["frame"]), "x": int(r["x"]), "y": int(r["y"])})
    return events


def save_events(path, events):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "evento", "frame", "x", "y"])
        for e in sorted(events, key=lambda e: e["frame"]):
            w.writerow([f"{e['t_s']:.3f}", e["evento"], e["frame"], e["x"], e["y"]])


def draw(frame, idx, fps, n_frames, roi, events, click, playing, speed, disp_scale):
    img = frame.copy()
    cx, cy, r = roi
    cv2.circle(img, (cx, cy), r, (0, 255, 255), 2)
    t = idx / fps
    # marcas cercanas en el tiempo (±0.5 s) para ver qué ya se anotó
    for e in events:
        if abs(e["frame"] - idx) <= int(fps * 0.5):
            col = (0, 200, 0) if e["evento"] == "in" else (0, 0, 255)
            cv2.circle(img, (e["x"], e["y"]), 18, col, 3)
            cv2.putText(img, e["evento"].upper(), (e["x"] + 20, e["y"] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2)
    if click is not None:
        cv2.drawMarker(img, click, (255, 0, 255), cv2.MARKER_CROSS, 30, 3)
    n_in = sum(e["evento"] == "in" for e in events)
    n_out = sum(e["evento"] == "out" for e in events)
    hud = [
        f"t = {t:6.2f} s   frame {idx}/{n_frames - 1}   {'PLAY' if playing else 'PAUSA'} x{speed}",
        f"IN: {n_in}   OUT: {n_out}   (clic en la abeja, luego i / o)",
    ]
    ov = img.copy()
    cv2.rectangle(ov, (0, 0), (img.shape[1], 90), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.6, img, 0.4, 0, img)
    for k, line in enumerate(hud):
        cv2.putText(img, line, (15, 35 + 38 * k), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    if disp_scale != 1.0:
        img = cv2.resize(img, None, fx=disp_scale, fy=disp_scale, interpolation=cv2.INTER_AREA)
    return img


def main():
    ap = argparse.ArgumentParser(description="Anotación manual de entradas/salidas")
    ap.add_argument("--video", required=True)
    ap.add_argument("--roi-x", type=int, required=True)
    ap.add_argument("--roi-y", type=int, required=True)
    ap.add_argument("--roi-r", type=int, required=True)
    ap.add_argument("--out", default="data/gt_eventos.csv")
    ap.add_argument("--start", type=float, default=0.0, help="segundo inicial")
    ap.add_argument("--max-width", type=int, default=1280, help="ancho máximo de la ventana")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"No se pudo abrir {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    disp_scale = min(1.0, a.max_width / w)

    events = load_events(a.out)
    if events:
        print(f"Retomando {len(events)} eventos de {a.out}")

    state = {"click": None}

    def on_mouse(ev, x, y, flags, param):
        if ev == cv2.EVENT_LBUTTONDOWN:
            state["click"] = (int(x / disp_scale), int(y / disp_scale))

    cv2.namedWindow(WIN, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WIN, on_mouse)

    idx = int(a.start * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    playing, speed_i = False, 1          # arranca en pausa a x0.25

    def seek(target):
        nonlocal idx, frame
        target = max(0, min(n_frames - 1, target))
        if target == idx + 1:
            ok_, f_ = cap.read()
        else:
            cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            ok_, f_ = cap.read()
        if ok_:
            idx, frame = target, f_
        return ok_

    while ok:
        speed = SPEEDS[speed_i]
        cv2.imshow(WIN, draw(frame, idx, fps, n_frames, (a.roi_x, a.roi_y, a.roi_r),
                             events, state["click"], playing, speed, disp_scale))
        delay = max(1, int(1000 / (fps * speed))) if playing else 30
        k = cv2.waitKeyEx(delay)
        ch = k & 0xFF if k != -1 else -1

        if k == -1:
            if playing and not seek(idx + 1):
                playing = False
            continue
        if ch in (ord("q"), 27):
            break
        elif ch == ord(" "):
            playing = not playing
        elif ch == ord("d") or k in KEY_RIGHT:
            playing = False
            seek(idx + 1)
        elif ch == ord("a") or k in KEY_LEFT:
            playing = False
            seek(idx - 1)
        elif ch == ord("l"):
            seek(idx + int(fps))
        elif ch == ord("j"):
            seek(idx - int(fps))
        elif ch in (ord("+"), ord("=")):
            speed_i = min(len(SPEEDS) - 1, speed_i + 1)
        elif ch in (ord("-"), ord("_")):
            speed_i = max(0, speed_i - 1)
        elif ch in (ord("i"), ord("o")):
            pos = state["click"] or (a.roi_x, a.roi_y)
            kind = "in" if ch == ord("i") else "out"
            events.append({"t_s": idx / fps, "evento": kind, "frame": idx, "x": pos[0], "y": pos[1]})
            state["click"] = None
            print(f"{kind.upper():3s} t={idx / fps:6.2f}s frame={idx} pos={pos}")
        elif ch == ord("z") and events:
            e = events.pop()
            print(f"Deshecho: {e['evento']} t={e['t_s']:.2f}s")
        elif ch == ord("s"):
            save_events(a.out, events)
            print(f"Guardado ({len(events)} eventos) en {a.out}")

    save_events(a.out, events)
    n_in = sum(e["evento"] == "in" for e in events)
    print(f"Guardado {a.out}: {n_in} IN, {len(events) - n_in} OUT. Último frame visto: {idx} "
          f"(t={idx / fps:.2f}s). Para seguir desde ahí usa --start {idx / fps:.1f}")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
