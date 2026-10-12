"""
Editor de cajas YOLO para los frames de despegue (data/despegues/train).

Se hace en local para que la etiqueta sea SIEMPRE la misma que el resto del
dataset: el nombre sale de classes.txt al subir con edge-impulse-uploader,
no se escribe a mano.

En cada imagen:
  - Cajas VERDES: abejas ya etiquetadas (pre-etiquetas del modelo o tuyas).
  - Círculo MAGENTA: dónde anotaste la salida (la abeja que despega está cerca).

CONTROLES
---------
  arrastrar (clic izq.)   dibujar una caja nueva
  clic derecho            borrar la caja bajo el cursor
  x                       zoom x2 alrededor del círculo magenta (otra vez = salir)
  z                       deshacer la última caja dibujada
  n / d / →               guardar y pasar a la siguiente imagen
  p / a / ←               guardar y volver a la anterior
  q / Esc                 guardar y salir

El avance se recuerda en revisadas.txt: al volver a abrir, sigue desde la
primera imagen no revisada.

Uso:
  python tools/etiquetar_cajas.py --dir data/despegues/train --gt data/gt_0040-1.csv
"""
import argparse
import csv
import glob
import os
import re

import cv2

KEY_LEFT = {2424832, 65361}
KEY_RIGHT = {2555904, 65363}
WIN = "Etiquetar cajas - Abeja"


def read_boxes(path, w, h):
    boxes = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            p = line.split()
            if len(p) == 5:
                cx, cy, bw, bh = (float(v) for v in p[1:])
                boxes.append([(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h])
    return boxes


def write_boxes(path, boxes, w, h):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for x0, y0, x1, y1 in boxes:
            x0, x1 = sorted((max(0, x0), min(w, x1)))
            y0, y1 = sorted((max(0, y0), min(h, y1)))
            if x1 - x0 < 3 or y1 - y0 < 3:
                continue
            f.write(f"0 {(x0 + x1) / 2 / w:.6f} {(y0 + y1) / 2 / h:.6f} {(x1 - x0) / w:.6f} {(y1 - y0) / h:.6f}\n")


def load_hints(gt_path, window):
    """{frame: [(x, y)]} con las salidas anotadas cercanas a cada frame."""
    outs = []
    if gt_path and os.path.exists(gt_path):
        for r in csv.DictReader(open(gt_path, newline="", encoding="utf-8-sig")):
            if r["evento"].strip().lower() == "out":
                outs.append((int(r["frame"]), int(r["x"]), int(r["y"])))
    return lambda fr: [(x, y) for f, x, y in outs if abs(f - fr) <= window]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/despegues/train")
    ap.add_argument("--gt", default="data/gt_0040-1.csv")
    ap.add_argument("--max-width", type=int, default=1280)
    a = ap.parse_args()

    images = sorted(glob.glob(os.path.join(a.dir, "*.png")) + glob.glob(os.path.join(a.dir, "*.jpg")))
    if not images:
        raise SystemExit(f"No hay imágenes en {a.dir}")
    done_path = os.path.join(os.path.dirname(os.path.abspath(a.dir)), "revisadas.txt")
    done = set(open(done_path, encoding="utf-8").read().split()) if os.path.exists(done_path) else set()
    hints_for = load_hints(a.gt, window=8)

    i = next((k for k, p in enumerate(images) if os.path.basename(p) not in done), 0)
    st = {"drag": None, "cur": None, "boxes": [], "added": [], "zoom": False, "view": (0, 0, 1.0)}

    def to_img(x, y):
        ox, oy, s = st["view"]
        return ox + x / s, oy + y / s

    def on_mouse(ev, x, y, flags, param):
        ix, iy = to_img(x, y)
        if ev == cv2.EVENT_LBUTTONDOWN:
            st["drag"] = (ix, iy)
            st["cur"] = (ix, iy)
        elif ev == cv2.EVENT_MOUSEMOVE and st["drag"]:
            st["cur"] = (ix, iy)
        elif ev == cv2.EVENT_LBUTTONUP and st["drag"]:
            x0, y0 = st["drag"]
            if abs(ix - x0) > 4 and abs(iy - y0) > 4:
                st["boxes"].append([min(x0, ix), min(y0, iy), max(x0, ix), max(y0, iy)])
                st["added"].append(st["boxes"][-1])
            st["drag"] = st["cur"] = None
        elif ev == cv2.EVENT_RBUTTONDOWN:
            inside = [b for b in st["boxes"] if b[0] <= ix <= b[2] and b[1] <= iy <= b[3]]
            if inside:
                small = min(inside, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
                st["boxes"].remove(small)

    cv2.namedWindow(WIN, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WIN, on_mouse)

    while True:
        path = images[i]
        name = os.path.basename(path)
        txt = os.path.splitext(path)[0] + ".txt"
        img = cv2.imread(path)
        h, w = img.shape[:2]
        st["boxes"] = read_boxes(txt, w, h)
        st["added"] = []
        st["zoom"] = False
        m = re.search(r"_f(\d+)", name)
        hints = hints_for(int(m.group(1))) if m else []
        base_s = min(1.0, a.max_width / w)
        st["view"] = (0, 0, base_s)
        action = None

        while action is None:
            ox, oy, s = st["view"]
            vw, vh = int(w * base_s / s), int(h * base_s / s)
            crop = img[int(oy):int(oy) + vh, int(ox):int(ox) + vw].copy()
            vis = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)

            def P(x, y):
                return int((x - ox) * s), int((y - oy) * s)

            for x, y in hints:
                cv2.circle(vis, P(x, y), int(45 * s), (255, 0, 255), 2)
            for b in st["boxes"]:
                cv2.rectangle(vis, P(b[0], b[1]), P(b[2], b[3]), (0, 255, 0), 2)
            if st["drag"] and st["cur"]:
                cv2.rectangle(vis, P(*st["drag"]), P(*st["cur"]), (0, 255, 255), 1)
            n_done = len(done | {name}) if name in done else len(done)
            info = f"{i + 1}/{len(images)}  {name}  cajas: {len(st['boxes'])}  revisadas: {n_done}  {'ZOOM x2' if st['zoom'] else ''}"
            cv2.rectangle(vis, (0, 0), (vis.shape[1], 34), (0, 0, 0), -1)
            cv2.putText(vis, info, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(WIN, vis)

            k = cv2.waitKeyEx(20)
            if k == -1:
                continue
            ch = k & 0xFF
            if ch in (ord("q"), 27):
                action = "quit"
            elif ch in (ord("n"), ord("d")) or k in KEY_RIGHT:
                action = "next"
            elif ch in (ord("p"), ord("a")) or k in KEY_LEFT:
                action = "prev"
            elif ch == ord("z") and st["added"]:
                b = st["added"].pop()
                if b in st["boxes"]:
                    st["boxes"].remove(b)
            elif ch == ord("x"):
                st["zoom"] = not st["zoom"]
                if st["zoom"]:
                    cx, cy = hints[0] if hints else (w / 2, h / 2)
                    s2 = base_s * 2
                    vw2, vh2 = w * base_s / s2, h * base_s / s2
                    st["view"] = (min(max(0, cx - vw2 / 2), w - vw2), min(max(0, cy - vh2 / 2), h - vh2), s2)
                else:
                    st["view"] = (0, 0, base_s)

        write_boxes(txt, st["boxes"], w, h)
        done.add(name)
        with open(done_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(done)))
        if action == "quit":
            break
        i = min(len(images) - 1, i + 1) if action == "next" else max(0, i - 1)

    cv2.destroyAllWindows()
    print(f"Revisadas {len(done)}/{len(images)} imágenes. Avance guardado en {done_path}")


if __name__ == "__main__":
    main()
