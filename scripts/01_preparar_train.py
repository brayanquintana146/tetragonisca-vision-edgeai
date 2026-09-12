#!/usr/bin/env python3







# -*- coding: utf-8 -*-
"""
Script 1: Preparar Train y Balanceo de Fondo (50 Parches)
----------------------------------------------------------
1. Copia todas las imágenes y etiquetas de 'train' (desde data/raw) a 'data/processed/train/'.
2. Toma la PRIMERA imagen de 'data/processed/train/' (ordenada alfabéticamente).
3. Asegura que la etiqueta (.txt) de esa primera imagen esté VACÍA en 'data/processed/train/'.
4. Genera 50 parches de 320x320 px a partir de esa primera imagen y les asigna etiquetas .txt VACÍAS.
"""

import os
import sys
import shutil
import random
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌ Error: Se requiere la librería Pillow. Instálala con: pip install Pillow")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_TRAIN_DIR = BASE_DIR / "data" / "processed" / "train"

def preparar_train_y_balancear(num_parches=50, patch_size=(320, 320)):
    # 1. Limpiar y crear carpeta de destino data/processed/train
    if PROCESSED_TRAIN_DIR.exists():
        shutil.rmtree(PROCESSED_TRAIN_DIR)
    PROCESSED_TRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # Crear classes.txt con la clase Abeja
    with open(PROCESSED_TRAIN_DIR / "classes.txt", "w", encoding="utf-8") as f:
        f.write("Abeja\n")

    print(f"📁 Carpeta de destino preparada: {PROCESSED_TRAIN_DIR}")

    # 2. Buscar carpeta 'train' dentro de data/raw/
    carpetas_train_raw = [p for p in RAW_DIR.rglob("*") if p.is_dir() and p.name.lower() == "train"]
    if not carpetas_train_raw:
        carpetas_train_raw = [RAW_DIR]

    extensiones_img = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']
    imagenes_encontradas = []
    for c in carpetas_train_raw:
        for ext in extensiones_img:
            imagenes_encontradas.extend(c.rglob(ext))

    imagenes_encontradas = sorted(list(dict.fromkeys(imagenes_encontradas)), key=lambda x: x.name.lower())

    if not imagenes_encontradas:
        print(f"⚠️ No se encontraron imágenes de train en '{RAW_DIR}'. Asegúrate de descomprimir el ZIP ahí.")
        return

    # Copiar todas las imágenes y sus .txt a data/processed/train
    print(f"📦 Copiando {len(imagenes_encontradas)} imágenes y etiquetas a '{PROCESSED_TRAIN_DIR}'...")
    for img_path in imagenes_encontradas:
        dest_img = PROCESSED_TRAIN_DIR / img_path.name
        shutil.copy2(img_path, dest_img)

        txt_name = img_path.stem + ".txt"
        label_path = img_path.parent / txt_name
        if not label_path.exists() and img_path.parent.name == "images":
            label_path = img_path.parent.parent / "labels" / txt_name
        elif not label_path.exists():
            posibles = list(RAW_DIR.rglob(txt_name))
            if posibles:
                label_path = posibles[0]

        dest_label = PROCESSED_TRAIN_DIR / txt_name
        if label_path.exists():
            shutil.copy2(label_path, dest_label)
        else:
            dest_label.touch()

    # 3. Seleccionar la PRIMERA imagen de train por orden alfabético
    imagenes_procesadas = sorted([
        f for f in PROCESSED_TRAIN_DIR.glob("*")
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png'] and "bg_unknown" not in f.name.lower()
    ], key=lambda x: x.name.lower())

    primera_imagen = imagenes_procesadas[0]
    print(f"🪵 Primera imagen seleccionada para fondo limpia: '{primera_imagen.name}'")

    # 4. Asegurar que la etiqueta .txt de la primera imagen quede VACÍA
    etiqueta_primera_imagen = PROCESSED_TRAIN_DIR / (primera_imagen.stem + ".txt")
    with open(etiqueta_primera_imagen, "w", encoding="utf-8") as f:
        f.write("")  # Sobrescribir con archivo vacío
    print(f"📄 Etiqueta de '{primera_imagen.name}' vaciada (.txt de clase negativa).")

    # 5. Generar 50 parches aleatorios a partir de esta primera imagen
    try:
        with Image.open(primera_imagen) as img:
            img = img.convert("RGB")
            w, h = img.size
            pw, ph = patch_size

            if w < pw or h < ph:
                pw, ph = min(w, pw), min(h, ph)

            random.seed(42)
            for i in range(1, num_parches + 1):
                x = random.randint(0, max(0, w - pw))
                y = random.randint(0, max(0, h - ph))

                crop_box = (x, y, x + pw, y + ph)
                patch = img.crop(crop_box)

                patch_name = f"bg_unknown_patch_{i:03d}.jpg"
                dest_img_path = PROCESSED_TRAIN_DIR / patch_name
                patch.save(dest_img_path, format="JPEG", quality=95)

                # Etiqueta .txt vacía
                dest_label_path = PROCESSED_TRAIN_DIR / f"bg_unknown_patch_{i:03d}.txt"
                dest_label_path.touch()

        print(f"✅ Se inyectaron {num_parches} parches de fondo con etiquetas vacías en '{PROCESSED_TRAIN_DIR}'.")

    except Exception as e:
        print(f"⚠️ Error al procesar parches de fondo: {e}")

    # Resumen
    archivos = list(PROCESSED_TRAIN_DIR.glob("*"))
    imgs = [f for f in archivos if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
    lbls = [f for f in archivos if f.suffix.lower() == '.txt' and f.name != 'classes.txt']
    print("\n" + "="*60)
    print(f"📊 RESUMEN 'train': {len(imgs)} imágenes | {len(lbls)} etiquetas .txt")
    print("="*60)

if __name__ == "__main__":
    preparar_train_y_balancear(num_parches=50, patch_size=(320, 320))
