#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 2: Copiar Valid a Processed Train
----------------------------------------
Proyecto: Tetragonisca Vision EdgeAI
Propósito:
  - Lee todas las imágenes y etiquetas .txt de la carpeta 'valid' dentro de 'data/raw/'.
  - Las anexa/copia directamente dentro de 'data/processed/train/'.
  - Conserva todas las imágenes y parches previamente procesados en 'data/processed/train/'.
"""

import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_TRAIN_DIR = BASE_DIR / "data" / "processed" / "train"

def copiar_valid_a_train():
    if not PROCESSED_TRAIN_DIR.exists():
        print(f"⚠️ La carpeta '{PROCESSED_TRAIN_DIR}' no existe. Ejecuta primero '01_preparar_train.py'.")
        return

    # Buscar subcarpetas 'valid' o 'val' en data/raw/
    carpetas_valid_raw = [
        p for p in RAW_DIR.rglob("*") 
        if p.is_dir() and p.name.lower() in ["valid", "val"]
    ]

    if not carpetas_valid_raw:
        print(f"⚠️ No se encontró la carpeta 'valid' o 'val' dentro de '{RAW_DIR}'.")
        return

    extensiones_img = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']
    imagenes_encontradas = []
    for c in carpetas_valid_raw:
        for ext in extensiones_img:
            imagenes_encontradas.extend(c.rglob(ext))

    imagenes_encontradas = sorted(list(dict.fromkeys(imagenes_encontradas)), key=lambda x: x.name.lower())

    if not imagenes_encontradas:
        print(f"⚠️ No se encontraron imágenes en las carpetas 'valid' de '{RAW_DIR}'.")
        return

    print(f"📦 Anexando {len(imagenes_encontradas)} imágenes y etiquetas de 'valid' a '{PROCESSED_TRAIN_DIR}'...")
    copiadas = 0

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
        copiadas += 1

    # Resumen
    archivos = list(PROCESSED_TRAIN_DIR.glob("*"))
    imgs = [f for f in archivos if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
    lbls = [f for f in archivos if f.suffix.lower() == '.txt' and f.name != 'classes.txt']

    print("\n" + "="*60)
    print(f"✅ SCRIPT 02 COMPLETADO: Se copiaron {copiadas} imágenes desde 'valid'.")
    print(f"📊 NUEVO TOTAL EN 'data/processed/train/': {len(imgs)} imágenes | {len(lbls)} etiquetas .txt")
    print("="*60 + "\n")

if __name__ == "__main__":
    copiar_valid_a_train()
