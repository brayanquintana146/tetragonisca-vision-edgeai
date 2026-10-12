"""
Renombra etiquetas de cajas (bounding boxes) en TODO un proyecto de Edge Impulse.

Caso de uso: el dataset se subió con un classes.txt de Windows ("Abeja\\r\\n") y
las cajas quedaron con la etiqueta "Abeja\\r" (con un retorno de carro invisible).
Las cajas dibujadas a mano en Studio quedan como "Abeja", así que aparecen dos
clases distintas. Este script unifica todo en "Abeja".

Usa la API de Edge Impulse:
  GET  /v1/api/{projectId}/raw-data                          (listar muestras y sus cajas)
  POST /v1/api/{projectId}/raw-data/batch/edit-bounding-boxes (renombrar en lote)

Por defecto SOLO muestra qué etiquetas hay y qué cambiaría (no modifica nada).
Para aplicar el cambio agrega --apply.

Uso (PowerShell):
  $env:EI_API_KEY = "ei_..."            # Dashboard > Keys del proyecto
  python tools/renombrar_etiqueta_ei.py --project-id 1108884
  python tools/renombrar_etiqueta_ei.py --project-id 1108884 --apply

Recomendado: antes de --apply, guarda una versión del proyecto (Versioning).
"""
import argparse
import collections
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://studio.edgeimpulse.com/v1/api"


def call(method, path, api_key, params=None, body=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Error HTTP {e.code} en {method} {path}: {e.read().decode('utf-8', 'replace')}")
    if isinstance(out, dict) and out.get("success") is False:
        raise SystemExit(f"La API respondió con error en {method} {path}: {out.get('error')}")
    return out


def count_labels(project_id, api_key, category="all", page=500):
    """Cuenta cajas por etiqueta exacta (incluye caracteres invisibles)."""
    labels = collections.Counter()
    samples_per_label = collections.Counter()
    offset, n_samples = 0, 0
    while True:
        out = call("GET", f"{project_id}/raw-data", api_key,
                   params={"category": category, "limit": page, "offset": offset})
        samples = out.get("samples", [])
        for s in samples:
            seen = set()
            for bb in s.get("boundingBoxes", []) or []:
                labels[bb["label"]] += 1
                seen.add(bb["label"])
            for lb in seen:
                samples_per_label[lb] += 1
        n_samples += len(samples)
        if len(samples) < page:
            break
        offset += page
    return labels, samples_per_label, n_samples


def show(labels, samples_per_label, n_samples):
    print(f"Muestras revisadas: {n_samples}")
    print(f"{'etiqueta exacta (repr)':30s} {'cajas':>8s} {'muestras':>9s}")
    for lb, n in labels.most_common():
        print(f"{repr(lb):30s} {n:8d} {samples_per_label[lb]:9d}")


def main():
    ap = argparse.ArgumentParser(description="Renombrar etiquetas de cajas en Edge Impulse")
    ap.add_argument("--project-id", required=True, type=int, help="ID del proyecto (Dashboard / URL de Studio)")
    ap.add_argument("--api-key", default=os.environ.get("EI_API_KEY"),
                    help="API key del proyecto (o variable de entorno EI_API_KEY)")
    ap.add_argument("--new", default="Abeja", help="nombre final de la etiqueta")
    ap.add_argument("--old", action="append", default=None,
                    help="etiqueta a reemplazar (repetible). Por defecto: toda etiqueta que, "
                         "quitando espacios/\\r, sea igual a --new pero no idéntica")
    ap.add_argument("--apply", action="store_true", help="aplicar el cambio (sin esto solo muestra)")
    a = ap.parse_args()

    if not a.api_key:
        raise SystemExit("Falta la API key: usa --api-key o define la variable EI_API_KEY")

    print("Leyendo etiquetas del proyecto...")
    labels, per_sample, n = count_labels(a.project_id, a.api_key)
    show(labels, per_sample, n)

    old = a.old or [lb for lb in labels if lb.strip() == a.new and lb != a.new]
    old = [lb for lb in old if lb in labels]
    if not old:
        print(f"\nNo hay nada que renombrar: todas las cajas ya se llaman {a.new!r}.")
        return
    total = sum(labels[lb] for lb in old)
    print(f"\nSe renombrarían {total} cajas: {', '.join(repr(lb) for lb in old)} -> {a.new!r}")

    if not a.apply:
        print("Modo prueba: no se cambió nada. Vuelve a correr con --apply para aplicarlo.")
        return

    out = call("POST", f"{a.project_id}/raw-data/batch/edit-bounding-boxes", a.api_key,
               params={"category": "all"}, body={"oldLabels": old, "newLabel": a.new})
    if out.get("id"):
        print(f"Edge Impulse inició un trabajo en lote (job {out['id']}). Esperando a que termine...")
    else:
        print("Cambio aplicado.")

    # Verificar: volver a contar hasta que no queden etiquetas viejas (máx. ~3 min)
    for _ in range(18):
        time.sleep(10 if out.get("id") else 2)
        labels, per_sample, n = count_labels(a.project_id, a.api_key)
        if not any(lb in labels for lb in old):
            print("\nListo. Etiquetas actuales:")
            show(labels, per_sample, n)
            return
    print("\nEl trabajo sigue en curso o no aplicó todo. Revisa en Studio y vuelve a correr sin --apply para ver el estado.")
    show(labels, per_sample, n)


if __name__ == "__main__":
    sys.exit(main())
