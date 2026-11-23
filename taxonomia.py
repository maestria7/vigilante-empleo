"""Áreas de especialidad (más finas que los temas del grupo) para el bot con formulario.

Clave de área = "<etapa>:<área>", por ejemplo "sec:geohist". Cada oferta puede tener varias.
La suscripción de una persona guarda claves concretas o el comodín "<etapa>:*" (todas las de esa etapa).
`python3 taxonomia.py` regenera taxonomia.json, que usa el formulario del bot.
"""
import json
import re
from pathlib import Path

from clasificar import _n

TAXONOMIA = [
    {"id": "inf", "nombre": "Infantil", "areas": [("general", "Educación Infantil")]},
    {"id": "pri", "nombre": "Primaria", "areas": [
        ("general", "Maestro/a de Primaria (tutoría)"), ("ef", "Educación Física"), ("ing", "Inglés"),
        ("fra", "Francés / Alemán"), ("mus", "Música"), ("rel", "Religión")]},
    {"id": "sec", "nombre": "Secundaria y Bachillerato", "areas": [
        ("general", "Secundaria (sin asignatura concreta)"), ("lengua", "Lengua y Literatura"), ("mat", "Matemáticas"),
        ("geohist", "Geografía e Historia"), ("biogeo", "Biología y Geología"), ("fq", "Física y Química"),
        ("tec", "Tecnología"), ("inf", "Informática"), ("ing", "Inglés"), ("fra", "Francés / Alemán"),
        ("ef", "Educación Física"), ("mus", "Música"), ("plas", "Plástica y Dibujo"), ("fil", "Filosofía y Valores"),
        ("eco", "Economía y Empresa"), ("lat", "Latín y Cultura Clásica"), ("rel", "Religión")]},
    {"id": "fp", "nombre": "Formación Profesional", "areas": [
        ("general", "FP (sin familia concreta)"), ("sanidad", "Sanidad"), ("inf", "Informática"),
        ("admin", "Administración y Gestión"), ("elec", "Electricidad, Mecánica y Mantenimiento"),
        ("serv", "Servicios socioculturales y Educación Infantil"), ("hosteleria", "Hostelería y Turismo"),
        ("imagen", "Imagen personal"), ("com", "Comercio y Logística")]},
    {"id": "esp", "nombre": "Apoyo y orientación", "areas": [
        ("pt", "Pedagogía Terapéutica (PT)"), ("al", "Audición y Lenguaje (AL)"),
        ("ee", "Educación Especial"), ("ori", "Orientación y Psicología")]},
]

_INF = r"infantil|preschool|\b0-3\b|primer ciclo"
_PRI = r"primaria|maestr"
_SEC = r"secundaria|\beso\b|bachiller"
_FP = r"\bfp\b|formacion profesional|ciclo formativo|cfgm|cfgs"
# asignaturas que existen en primaria y secundaria
_COMUNES = {
    "ef": r"educacion fisica|ed\.? ?fisica|\bef\b|actividad fisica",
    "ing": r"ingles|english|lengua extranjera",
    "fra": r"frances|aleman",
    "mus": r"musica|musical",
    "rel": r"religion",
}
_SOLO_SEC = {
    "lengua": r"lengua castellana|lengua y literatura|\blengua\b(?! extranjera)|literatura",
    "mat": r"matematicas",
    "geohist": r"geografia|historia|ciencias sociales",
    "biogeo": r"biologia|geologia|ciencias naturales",
    "fq": r"fisica y quimica|quimica|\bfisica\b(?! y)",
    "tec": r"tecnologia",
    "inf": r"informatica|programacion|digitalizacion",
    "plas": r"plastica|dibujo|artes plasticas|educacion artistica",
    "fil": r"filosofia|valores eticos",
    "eco": r"economia|empresa",
    "lat": r"\blatin\b|griego|cultura clasica",
}
_ESP = {
    "pt": r"pedagogia terap|\bpt\b",
    "al": r"audicion y lenguaje|logoped|\(al\)|\bal\b(?=\s*(?:-|/|\)|$))",
    "ee": r"educacion especial|necesidades educativas|\bneae\b|integracion social",
    "ori": r"orientacion|orientador|psicolog|pedagog(?!ia terap)",
}
_FAMILIAS = {
    "sanidad": r"sanidad|enfermeria|farmacia|laboratorio clinico|cuidados auxiliares",
    "inf": r"informatica|sistemas|\bdam\b|\bdaw\b|\basir\b|redes|programacion",
    "admin": r"administracion|gestion|finanzas|contabilidad",
    "elec": r"electricidad|electronica|automatizacion|mecanica|mantenimiento|soldadura|fabricacion",
    "serv": r"servicios socioculturales|educacion infantil|animacion|dependencia|integracion social",
    "hosteleria": r"hosteleria|cocina|turismo|restaurante",
    "imagen": r"peluqueria|estetica|imagen personal",
    "com": r"comercio|marketing|logistica|transporte",
}


def areas(titulo):
    """Claves de área de una oferta. Devuelve [] si no se reconoce ninguna."""
    t = _n(titulo[:150])
    inf, pri, sec, fp = (bool(re.search(r, t)) for r in (_INF, _PRI, _SEC, _FP))
    pri_explicita = bool(re.search(r"primaria", t))
    out = []

    def add(k):
        if k not in out:
            out.append(k)

    for k, rx in _ESP.items():
        if re.search(rx, t):
            add(f"esp:{k}")
    if fp:
        fam = [k for k, rx in _FAMILIAS.items() if re.search(rx, t)]
        for k in fam or ["general"]:
            add(f"fp:{k}")
    comunes = [k for k, rx in _COMUNES.items() if re.search(rx, t)]
    t_sin_ef = re.sub(_COMUNES["ef"], " ", t)  # «educación física» no es la asignatura de Física
    sec_asig = [k for k, rx in _SOLO_SEC.items() if re.search(rx, t_sin_ef)] if not fp else []
    for k in comunes:
        etapas = [e for e, on in (("pri", pri), ("sec", sec)) if on] or ["pri", "sec"]
        if inf and not (pri or sec):
            etapas = []
        for e in etapas:
            add(f"{e}:{k}")
    for k in sec_asig:
        add(f"sec:{k}")
    if inf and not comunes:
        add("inf:general")
    if pri_explicita and not comunes and not any(x.startswith("esp:") for x in out):
        add("pri:general")
    if sec and not comunes and not sec_asig and not fp:
        add("sec:general")
    if not out and re.search(_PRI, t):  # «maestro/a» a secas
        add("pri:general")
    return out


def exportar():
    datos = {"etapas": [{"id": e["id"], "nombre": e["nombre"],
                         "areas": [{"id": a, "nombre": n} for a, n in e["areas"]]} for e in TAXONOMIA]}
    (Path(__file__).parent / "taxonomia.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    exportar()
    print("taxonomia.json generado")
