"""Funciones que leen cada web de empleo y devuelven una lista de ofertas."""
import urllib.error, hashlib, html, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf8", errors="ignore")


def colegios_es(provincia):
    """Ofertas de la página de una provincia de colegios.es."""
    base = f"https://colegios.es/empleoprofesores/{provincia}/"
    h = get(base)
    out, vistos = [], set()
    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
        # las ofertas terminan en una fecha ddmmaaaa
        if re.search(r"-\d{8}/?$", href) and t and not t.lower().startswith("ver ") and href not in vistos:
            vistos.add(href)
            d = re.search(r"-(\d{2})(\d{2})(\d{4})/?$", href)
            pub = f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else None
            out.append({"id": href, "titulo": t, "url": href, "origen": f"colegios.es · {provincia}", "pub": pub})
    return out


def colejobs(provincia):
    """Ofertas de colegios concertados/privados en colejobs.es."""
    base = f"https://www.colejobs.es/ofertas-de-empleo/{provincia}/"
    h = get(base)
    out, vistos = [], set()
    for href, txt in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', h, re.S):
        if not re.search(r"ofertas-de-empleo/[^/]+-n[0-9A-Za-z]+/?$", href):
            continue
        url = urllib.parse.urljoin(base, href)
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", txt))).strip()
        if t and url not in vistos:
            vistos.add(url)
            out.append({"id": url, "titulo": t[:150], "url": url, "origen": f"Colejobs · {provincia}"})
    return out


def colejobs_nacional(paginas=6):
    """Listado nacional de colejobs.es (20 ofertas por página; la zona va en el texto)."""
    out, vistos = [], set()
    urls = ["https://www.colejobs.es/ofertas-de-empleo/"] + [f"https://www.colejobs.es/ofertas-de-empleo/paginador/{n}-{paginas}/" for n in range(2, paginas + 1)]
    for base in urls:
        try:
            h = get(base)
        except Exception:
            if base == urls[0]:
                raise
            continue
        for href, txt in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', h, re.S):
            if not re.search(r"ofertas-de-empleo/[^/]+-n[0-9A-Za-z]+/?$", href):
                continue
            url = urllib.parse.urljoin(base, href)
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", txt))).strip()
            if t and url not in vistos:
                vistos.add(url)
                out.append({"id": url, "titulo": t[:260], "url": url, "origen": "Colejobs"})
    return out


def _txt(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


_MINUSCULAS = {"de", "del", "la", "las", "el", "los", "en", "y", "o", "a", "para", "con", "por", "al", "un", "una", "e"}


def _titulo_normal(t):
    """Jobsora escribe los títulos con cada palabra en mayúscula («Profesor De Educación Física», «Educador/A»): se devuelve a su forma normal."""
    palabras = [w.lower() if i and w.lower() in _MINUSCULAS else w for i, w in enumerate(t.split())]
    return re.sub(r"/A\b", "/a", " ".join(palabras))


def jobsora(consulta, lugar):
    """Resultados de es.jobsora.com (agregador; incluye CEU, Loyola, Domestiko...).

    El título es SOLO el puesto (<h2>); la empresa, el lugar y un trozo de la descripción se guardan aparte y no se mezclan con el título
    (antes se cogía todo el texto de la tarjeta y se clasificaba mal)."""
    h = get(f"https://es.jobsora.com/empleos-{consulta}-{lugar}")
    out = []
    for m in re.finditer(r'<article[^>]*data-href="(https://es\.jobsora\.com/oferta-\d+)[^"]*"[^>]*>(.*?)</article>', h, re.S):
        a = m.group(2)
        t = re.search(r'<h2 class="c-job-item__title">(.*?)</h2>', a, re.S)
        titulo = _titulo_normal(_txt(t.group(1))) if t else ""
        if not titulo:
            continue
        infos = [_txt(x) for x in re.findall(r'<div class="c-job-item__info-item">(.*?)</div>', a, re.S)]
        d = re.search(r'<p class="c-job-item__description[^"]*">(.*?)</p>', a, re.S)
        out.append({"id": m.group(1), "titulo": titulo[:150], "url": m.group(1), "origen": "Jobsora",
                    "empresa": infos[0] if len(infos) > 1 else "", "lugar": infos[-1] if infos else "", "desc": _txt(d.group(1))[:300] if d else ""})
    return out


def edutalent():
    """Últimas ofertas de edutalent.es (centros concertados; ámbito nacional)."""
    h = get("https://edutalent.es/vacantes-madrid/")
    out, vistos = [], set()
    for bloque in h.split('<div class="offer"')[1:]:
        u = re.search(r"window\.location='([^']+)'", bloque)
        if not u or u.group(1) in vistos:
            continue
        url = u.group(1)
        vistos.add(url)
        h3 = re.search(r"<h3>(.*?)</h3>", bloque, re.S)
        t = _txt(h3.group(1)) if h3 else url.rstrip("/").split("/")[-1].replace("-", " ")
        resto = _txt(bloque[bloque.find("</h3>") + 5:])[:70] if h3 else ""
        out.append({"id": url, "titulo": f"{t} — {resto}"[:150], "url": url, "origen": "Edutalent (toda España)"})
    return out


def empleoo():
    """Ofertas de educación de empleoo.net (agregador; la web repite el mismo anuncio en muchas ciudades).

    Lee la categoría «Educación y formación» y unas búsquedas docentes. Las copias del mismo anuncio que
    solo cambian de ciudad (3 o más con el mismo comienzo de título) se juntan en una sola oferta."""
    paginas = [f"https://empleoo.net/job-category/educacion-y-formacion/{'' if n == 1 else f'page/{n}/'}" for n in range(1, 5)]
    paginas += [f"https://empleoo.net/trabajo/?s={urllib.parse.quote(q)}"
                for q in ("maestro", "educación física", "primaria", "infantil", "profesor")]
    ofertas, vistos = [], set()
    for p in paginas:
        try:
            h = get(p)
        except Exception:
            continue
        for art in re.findall(r"<article\b.*?</article>", h, re.S):
            u = re.search(r'href="(https://empleoo\.net/trabajo/[^"]+)"', art)
            t = re.search(r"<h\d[^>]*>.*?<a[^>]*>(.*?)</a>", art, re.S)
            if not u or not t or u.group(1) in vistos:
                continue
            vistos.add(u.group(1))
            ofertas.append((_txt(t.group(1)), u.group(1)))
    ajenas = ("jardiner", "barber", "peluquer", "autoescuela", "psiquiatra", "psicólogo", "médico", "enfermer",
              "camarer", "mcdonald", "conserje", "azafat", "administrativ", "comercial", "conductor", "optometr")
    ofertas = [(t, u) for t, u in ofertas if not any(x in t.lower() for x in ajenas)]
    grupos = {}
    for t, u in ofertas:
        grupos.setdefault(" ".join(t.lower().split()[:7]), []).append((t, u))
    out = []
    for lista in grupos.values():
        if len(lista) >= 3:  # mismo anuncio clonado por ciudades: una sola oferta
            pal = lista[0][0].split()[:7]
            while pal and pal[-1].lower() in ("en", "desde", "de", "para", "–", "-", "|"):
                pal.pop()
            t = " ".join(pal)
            out.append({"id": lista[0][1], "titulo": f"{t} (anuncio repetido en {len(lista)} ciudades, empresa sin identificar)"[:150],
                        "url": lista[0][1], "origen": "Empleoo.net"})
        else:
            out += [{"id": u, "titulo": t[:150], "url": u, "origen": "Empleoo.net"} for t, u in lista]
    return out


def escolapios_emaus():
    """Bolsa de empleo pública de Escolapios Emaús (Aragón, Navarra, País Vasco, La Rioja, Andalucía)."""
    base = "http://www.bolsadeempleo.escolapiosemaus.org/"
    h = get(base)
    out = []
    for fila in re.findall(r'<tr data-oferta-id="(\d+)">(.*?)</tr>', h, re.S):
        oid, cuerpo = fila
        celdas = [_txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", cuerpo, re.S)]
        if len(celdas) < 6:
            continue
        fecha, desc, _vac, _cand, lugar, prov = celdas[:6]
        d = re.match(r"(\d{2})/(\d{2})/(\d{4})", fecha)
        out.append({"id": f"{base}#oferta-{oid}", "titulo": f"{desc} — {lugar} ({prov})"[:150],
                    "url": f"{base}#oferta-{oid}", "origen": "Escolapios Emaús",
                    "pub": f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else None})
    return out


def maristas_iberica():
    """Bolsa pública de la Provincia Marista Ibérica (Cáceres, Castilla-La Mancha, Madrid, Aragón, País Vasco, Navarra, La Rioja)."""
    base = "https://trabajaconnosotros.maristasiberica.es"
    out, vistos = [], set()
    for pag in range(1, 9):
        try:
            h = get(f"{base}/?page={pag}&items=5")
        except urllib.error.HTTPError:
            break  # página inexistente: se acabaron las ofertas
        nuevos = 0
        for m in re.finditer(r"<a class='list-group-item ofportada' ttl_of='(.*?)' url_of='([^']+)'>(.*?)</a>", h, re.S):
            tit, url, cuerpo = html.unescape(m.group(1)).strip(), m.group(2), m.group(3)
            if url in vistos:
                continue
            vistos.add(url)
            nuevos += 1
            lugar = re.search(r"<small>(.*?)</small>", cuerpo, re.S)
            lugar = _txt(lugar.group(1)) if lugar else ""
            out.append({"id": base + url, "titulo": f"{tit} — {lugar}"[:150], "url": base + url, "origen": "Maristas Ibérica"})
        if not nuevos:
            break
    return out


def cdlmurcia():
    """Ofertas de empleo de Educación del Colegio de Doctores y Licenciados de Murcia."""
    url = "https://cdlmurcia.es/ofertas-de-empleo-de-educacion/"
    t = _txt(get(url))
    trozos = re.split(r"(?=Oferta de [^()]{3,80}\(\d\d/\d\d/\d{4}\))", t)
    out = []
    for z in trozos:
        m = re.match(r"(Oferta de [^()]{3,80}\(\d\d/\d\d/\d{4}\))\s*(.*)", z)
        if not m:
            continue
        pu = re.search(r"Puesto:\s*([^.]{3,90})", m.group(2))
        tit = m.group(1) + (" · " + pu.group(1) if pu else "")
        out.append({"id": f"{url}#{m.group(1)}{m.group(2)[:40]}", "titulo": tit, "url": url, "origen": "CDL Murcia"})
    return out


def talent(consulta, lugar):
    """Resultados de búsqueda en es.talent.com (agregador de ofertas)."""
    url = "https://es.talent.com/jobs?" + urllib.parse.urlencode({"k": consulta, "l": lugar})
    h = get(url)
    out = []
    for m in re.finditer(r'data-new-id="(\d+)".*?<h2[^>]*>(.*?)</h2>(?:.*?JobCard_company[^>]*>(.*?)</span>)?', h, re.S):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        emp = re.sub(r"<[^>]+>", "", m.group(3) or "").strip()
        link = "https://es.talent.com/view?id=" + m.group(1)
        if t:
            out.append({"id": link, "titulo": t + (f" — {emp}" if emp else ""), "url": link, "origen": f"Talent.com · {lugar}"})
    return out


def rss(url):
    root = ET.fromstring(get(url))
    out = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        titulo = html.unescape(it.findtext("title") or "").strip()
        out.append({"id": link or titulo, "titulo": titulo, "url": link, "origen": "alerta/RSS", "sin_filtro": True})
    for en in root.iter("{http://www.w3.org/2005/Atom}entry"):  # Google Alerts usa Atom
        a = en.find("{http://www.w3.org/2005/Atom}link")
        link = a.get("href") if a is not None else ""
        # Google Alerts envuelve el enlace real en google.com/url?url=...
        q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        link = q.get("url", [link])[0]
        titulo = html.unescape(re.sub(r"<[^>]+>", "", en.findtext("{http://www.w3.org/2005/Atom}title") or "")).strip()
        out.append({"id": link, "titulo": titulo, "url": link, "origen": "alerta Google", "sin_filtro": True})
    return out


def pagina_cambia(url):
    h = re.sub(r"\s+", " ", re.sub(r"<(script|style).*?</\1>", "", get(url), flags=re.S))
    huella = hashlib.sha1(h.encode()).hexdigest()[:12]
    return [{"id": f"{url}#{huella}", "titulo": "La página ha cambiado", "url": url, "origen": "página vigilada", "sin_filtro": True}]


