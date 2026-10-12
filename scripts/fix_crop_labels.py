"""
fix_crop_labels.py
──────────────────
Corrige las coordenadas YOLO (.txt) después de haber recortado las imágenes
con FastStone (o cualquier herramienta que haga un crop uniforme).

Procesa automáticamente las carpetas train/labels, valid/labels y test/labels.
"""

import os
import shutil


def fix_yolo_labels_in_folder(labels_dir, output_dir,
                               orig_w, orig_h,
                               crop_x, crop_y, crop_w, crop_h):
    """
    Lee todos los .txt de 'labels_dir', recalcula las coordenadas
    según el crop aplicado, y guarda los nuevos .txt en 'output_dir'.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    txt_files = [f for f in os.listdir(labels_dir)
                 if f.endswith('.txt') and f != "classes.txt"]

    count_procesados = 0
    count_eliminados = 0

    for txt_file in txt_files:
        ruta_in = os.path.join(labels_dir, txt_file)
        ruta_out = os.path.join(output_dir, txt_file)

        lineas_nuevas = []

        with open(ruta_in, 'r') as f:
            for linea in f:
                partes = linea.strip().split()
                if len(partes) < 5:
                    continue

                clase = partes[0]
                x_norm = float(partes[1])
                y_norm = float(partes[2])
                w_norm = float(partes[3])
                h_norm = float(partes[4])

                # 1. Des-normalizar a píxeles de la imagen original
                x_center = x_norm * orig_w
                y_center = y_norm * orig_h
                box_w = w_norm * orig_w
                box_h = h_norm * orig_h

                # 2. Calcular esquinas en coordenadas originales
                left = x_center - (box_w / 2)
                right = x_center + (box_w / 2)
                top = y_center - (box_h / 2)
                bottom = y_center + (box_h / 2)

                # 3. Trasladar al nuevo sistema de coordenadas del recorte
                new_left = left - crop_x
                new_right = right - crop_x
                new_top = top - crop_y
                new_bottom = bottom - crop_y

                # 4. Clipping: recortar cajas que se salen del nuevo límite
                new_left = max(0, min(new_left, crop_w))
                new_right = max(0, min(new_right, crop_w))
                new_top = max(0, min(new_top, crop_h))
                new_bottom = max(0, min(new_bottom, crop_h))

                new_box_w = new_right - new_left
                new_box_h = new_bottom - new_top

                # 5. Si la caja quedó muy pequeña o desapareció, la descartamos
                if new_box_w <= 2 or new_box_h <= 2:
                    count_eliminados += 1
                    continue

                # 6. Re-normalizar para el nuevo tamaño de imagen
                new_x_center_norm = (new_left + (new_box_w / 2)) / crop_w
                new_y_center_norm = (new_top + (new_box_h / 2)) / crop_h
                new_w_norm = new_box_w / crop_w
                new_h_norm = new_box_h / crop_h

                lineas_nuevas.append(
                    f"{clase} {new_x_center_norm:.6f} {new_y_center_norm:.6f} "
                    f"{new_w_norm:.6f} {new_h_norm:.6f}\n"
                )

        # Guardar archivo (vacío si no quedaron cajas)
        with open(ruta_out, 'w') as f:
            f.writelines(lineas_nuevas)

        count_procesados += 1

    return count_procesados, count_eliminados


if __name__ == "__main__":
    # ──────────────────────────────────────────────────────────────────
    # CONFIGURACIÓN — Ajusta estos valores según tu proyecto
    # ──────────────────────────────────────────────────────────────────

    # Ruta base del dataset (la carpeta que contiene train/, valid/, test/)
    DATASET_DIR = r"data\raw\001_Object_Detection_Raw\Dataset"

    # Carpeta donde se guardarán los .txt corregidos (misma estructura)
    OUTPUT_BASE = r"data\raw\001_Object_Detection_Raw\Dataset_labels_corregidos"

    # Dimensiones de la imagen ORIGINAL (antes del crop)
    ORIG_W = 1920
    ORIG_H = 1080

    # Parámetros del crop en FastStone
    CROP_X = 260    # Posición X (Left) del recorte
    CROP_Y = 100    # Posición Y (Top) del recorte
    CROP_W = 1280   # Ancho del recorte resultante
    CROP_H = 720    # Alto del recorte resultante

    # ──────────────────────────────────────────────────────────────────

    splits = ["train", "valid", "test"]
    total_procesados = 0
    total_eliminados = 0

    for split in splits:
        labels_in = os.path.join(DATASET_DIR, split, "labels")
        labels_out = os.path.join(OUTPUT_BASE, split, "labels")

        if not os.path.exists(labels_in):
            print(f"[!] No se encontro: {labels_in} -- saltando...")
            continue

        # Copiar classes.txt si existe
        classes_file = os.path.join(labels_in, "classes.txt")
        if os.path.exists(classes_file):
            os.makedirs(labels_out, exist_ok=True)
            shutil.copy2(classes_file, os.path.join(labels_out, "classes.txt"))

        print(f"\n[>] Procesando {split}/labels/ ...")
        procesados, eliminados = fix_yolo_labels_in_folder(
            labels_dir=labels_in,
            output_dir=labels_out,
            orig_w=ORIG_W,
            orig_h=ORIG_H,
            crop_x=CROP_X,
            crop_y=CROP_Y,
            crop_w=CROP_W,
            crop_h=CROP_H
        )
        total_procesados += procesados
        total_eliminados += eliminados
        print(f"   [OK] {procesados} archivos .txt corregidos")
        print(f"   [X]  {eliminados} cajas eliminadas (abejas fuera del recorte)")

    print(f"\n{'='*50}")
    print(f"TOTAL: {total_procesados} archivos procesados!")
    print(f"{total_eliminados} cajas eliminadas en total.")
    print(f"\nLos .txt corregidos estan en: {OUTPUT_BASE}")
    print(f"\nSiguiente paso: Reemplaza los .txt viejos de labels/ por estos nuevos")
    print(f"y sube todo a Edge Impulse junto con las fotos recortadas.")
