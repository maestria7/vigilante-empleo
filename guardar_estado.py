#!/usr/bin/env python3
"""Guarda el estado (ofertas ya vistas) en el repositorio sin conflictos.

Los flujos ligero y pesado pueden terminar a la vez: en vez de un rebase que falla, se fusiona
(unión de ids vistos, fecha más reciente de los límites) con lo último que haya en origin y se sube.
"""
import json, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).parent
FICHEROS = ["vistos.json", "vistos_publico.json", "limites.json", "publicadas.json", "salud.json", "metricas.json", "calidad.json"]


def sh(*a, check=True):
    return subprocess.run(a, cwd=AQUI, capture_output=True, text=True, check=check).stdout


def fusionar(a, b):
    if isinstance(a, list) or isinstance(b, list):
        return sorted(set(a or []) | set(b or []))
    if any(isinstance(v, dict) for v in list(a.values()) + list(b.values())):  # publicadas.json: id -> registro
        out = dict(b)
        for k, v in a.items():
            w = b.get(k)
            # si hay dos versiones, me quedo con la más avanzada (cerrada/vieja y con más mensajes)
            out[k] = v if not w or (bool(v.get("estado")), len(v.get("m", []))) >= (bool(w.get("estado")), len(w.get("m", []))) else w
        return out
    return {k: max(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b)}


for intento in range(5):
    sh("git", "fetch", "-q", "origin", "main")
    locales = {}
    for f in FICHEROS:
        p = AQUI / f
        locales[f] = json.loads(p.read_text()) if p.exists() else None
    sh("git", "reset", "-q", "--hard", "origin/main")
    for f, mio in locales.items():
        if mio is None:
            continue
        p = AQUI / f
        remoto = json.loads(p.read_text()) if p.exists() else type(mio)()
        p.write_text(json.dumps(fusionar(mio, remoto), ensure_ascii=False))
    sh("git", "add", *[f for f in FICHEROS if (AQUI / f).exists()])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=AQUI).returncode == 0:
        print("estado sin cambios")
        sys.exit(0)
    sh("git", "commit", "-q", "-m", "actualizar vistos")
    if subprocess.run(["git", "push", "-q"], cwd=AQUI).returncode == 0:
        print("estado guardado")
        sys.exit(0)
print("no se pudo guardar el estado", file=sys.stderr)
sys.exit(1)
