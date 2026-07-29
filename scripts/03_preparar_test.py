#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 3: Preparar Conjunto de Prueba (Test)
---------------------------------------------
Proyecto: Tetragonisca Vision EdgeAI
Propósito:
  - Crea/limpia la carpeta de destino 'data/processed/test/'.
  - Genera automáticamente el archivo 'classes.txt' en 'data/processed/test/'.
  - Busca todas las imágenes y etiquetas .txt en la carpeta 'test' de 'data/raw/'.
  - Copia las imágenes y etiquetas directamente a 'data/processed/test/'.
"""

import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_TEST_DIR = BASE_DIR / "data" / "processed" / "test"

def preparar_test():
    # 1. Crear / limpiar la carpeta data/processed/test/
    if PROCESSED_TEST_DIR.exists():
        shutil.rmtree(PROCESSED_TEST_DIR)
    PROCESSED_TEST_DIR.mkdir(parents=True, exist_ok=True)

    # Crear classes.txt con la clase Abeja
    with open(PROCESSED_TEST_DIR / "classes.txt", "w", encoding="utf-8") as f:
        f.write("Abeja\n")

    print(f"📁 Carpeta de destino preparada: {PROCESSED_TEST_DIR}")

    # 2. Buscar carpetas 'test' en data/raw/
    carpetas_test_raw = [
        p for p in RAW_DIR.rglob("*") 
        if p.is_dir() and p.name.lower() == "test"
    ]

    if not carpetas_test_raw:
        print(f"⚠️ No se encontró la carpeta 'test' dentro de '{RAW_DIR}'.")
        return

    extensiones_img = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']
    imagenes_encontradas = []
    for c in carpetas_test_raw:
        for ext in extensiones_img:
            imagenes_encontradas.extend(c.rglob(ext))

    imagenes_encontradas = sorted(list(dict.fromkeys(imagenes_encontradas)), key=lambda x: x.name.lower())

    if not imagenes_encontradas:
        print(f"⚠️ No se encontraron imágenes en las carpetas 'test' de '{RAW_DIR}'.")
        return

    print(f"📦 Copiando {len(imagenes_encontradas)} imágenes y etiquetas a '{PROCESSED_TEST_DIR}'...")
    copiadas = 0

    for img_path in imagenes_encontradas:
        dest_img = PROCESSED_TEST_DIR / img_path.name
        shutil.copy2(img_path, dest_img)

        txt_name = img_path.stem + ".txt"
        label_path = img_path.parent / txt_name
        if not label_path.exists() and img_path.parent.name == "images":
            label_path = img_path.parent.parent / "labels" / txt_name
        elif not label_path.exists():
            posibles = list(RAW_DIR.rglob(txt_name))
            if posibles:
                label_path = posibles

        dest_label = PROCESSED_TEST_DIR / txt_name
        if label_path.exists():
            shutil.copy2(label_path, dest_label)
        else:
            dest_label.touch()
        copiadas += 1

    # Resumen
    archivos = list(PROCESSED_TEST_DIR.glob("*"))
    imgs = [f for f in archivos if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
    lbls = [f for f in archivos if f.suffix.lower() == '.txt' and f.name != 'classes.txt']

    print("\n" + "="*60)
    print(f"✅ SCRIPT 03 COMPLETADO: Se copiaron {copiadas} imágenes a 'data/processed/test/'.")
    print(f"📊 RESUMEN 'test': {len(imgs)} imágenes | {len(lbls)} etiquetas .txt | classes.txt: ✅")
    print("="*60 + "\n")

if __name__ == "__main__":
    preparar_test()
