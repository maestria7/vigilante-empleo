"""Clasifica una oferta por especialidad (temas) y por comunidad autónoma."""
import re
import unicodedata

from provincias import COMUNIDADES, EXTRA_LUGARES, PROVINCIAS


def _n(s):
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


# Orden = prioridad. (tema, expresión sobre el texto sin tildes y en minúsculas)
ESPECIFICAS = [
    ("PT", r"pedagogia terap|\bpt\b|terapeutic"),
    ("Audición y Lenguaje", r"audicion y lenguaje|logoped|\(al\)|\bal\b(?=\s*(?:-|/|\)|$))|\bmaestr[oa]/?a? al\b"),
    ("Educación Especial", r"educacion especial|necesidades educativas|neae|integracion social"),
    ("Educación Física", r"educacion fisica|ed\.? ?fisica|\bef\b|actividad fisica|deport"),
    ("Música", r"musica|musical|conservatorio|violonchelo|violin|piano|guitarra|canto\b"),
    ("Idiomas", r"ingles|english|frances|aleman|bilingue|lengua extranjera|idioma"),
    ("Infantil", r"infantil|preschool|0-3|primer ciclo"),
]
PRIMARIA = r"primaria|maestro|maestra|maestr"
GENERALES = [
    ("Secundaria", r"secundaria|\beso\b|bachiller|matematicas|lengua castellana|lengua y literatura|fisica y quimica|biologia|geologia|geografia|historia|filosofia|economia|\blatin\b|tecnologia|informatica|dibujo|plastica|ciencias naturales"),
    ("FP", r"\bfp\b|formacion profesional|ciclo formativo|cfgm|cfgs"),
    ("Religión", r"religion"),
    ("Orientación", r"orientacion|orientador|psicolog|pedagog"),
]
ES_DOCENTE = r"profesor|\bprofe\b|docente|maestr|educador|orientador|psicolog|logoped|tutor|colegio|escuela|primaria|infantil|\beso\b|bachiller|formador|ensenanza|educacion"
EXCLUIR = r"dietista|candidaturas espont|auxiliar de|comedor|internship|bucodental|electromecanic|clases particulares|profesor particular|profesora particular|particular|monitor|limpieza|cocin|conductor|administrativ|recepcion|taller|camarer|dependient|socorrista|consultor|sap\b|comercial|enfermer"

TEMAS = ["Primaria", "Educación Física", "PT", "Audición y Lenguaje", "Educación Especial",
         "Música", "Idiomas", "Infantil", "Secundaria", "FP", "Religión", "Orientación", "Otros"]


def temas(titulo, max_temas=2):
    t = _n(titulo[:110])
    out = []
    if re.search(r"primaria", t):
        out.append("Primaria")
    for nombre, rx in ESPECIFICAS:
        if re.search(rx, t) and nombre not in out:
            out.append(nombre)
    if not out and re.search(PRIMARIA, t):
        out.append("Primaria")
    if not out:
        for nombre, rx in GENERALES:
            if re.search(rx, t):
                out.append(nombre)
                break
    return (out or ["Otros"])[:max_temas]


def es_docente(titulo):
    t = _n(titulo)
    return bool(re.search(ES_DOCENTE, t)) and not re.search(EXCLUIR, t)


def comunidad_y_provincia(texto):
    """Deduce (código_comunidad, provincia) a partir de un texto libre, o (None, None)."""
    t = _n(texto)
    for nombre, cod, *_ in PROVINCIAS:
        n = _n(nombre)
        if len(n) > 4 and re.search(r"\b" + re.escape(n) + r"\b", t):
            return cod, nombre
    for cod, palabras in EXTRA_LUGARES.items():
        for p in palabras:
            if _n(p) in t:
                return cod, None
    return None, None


def hashtags(cod, provincia):
    tags = []
    if cod:
        tags += [f"#{cod}", "#" + re.sub(r"\W", "", _n(COMUNIDADES[cod]).title().replace(" ", ""))]
    if provincia:
        tags.append("#" + re.sub(r"\W", "", _n(provincia).title()))
    return tags or ["#SinZona"]


def tag_tema(tema):
    return "#" + re.sub(r"\W", "", _n(tema).title())
