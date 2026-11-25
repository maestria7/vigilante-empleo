"""Pruebas del vigilante (sin red). Uso: python3 -m unittest -v test_vigilante"""
import json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

import calidad
import clasificar as C
import enlaces as E
import fuentes as F
import horario
import vigilante as V


def ofertas(n, agregador, prefijo):
    return [{"id": f"{prefijo}{i}", "titulo": f"Profesor de Matemáticas {prefijo}{i}", "url": f"https://x.es/{prefijo}{i}", "origen": prefijo, "agregador": agregador} for i in range(n)]


class Reparto(unittest.TestCase):
    def test_una_avalancha_solo_publica_el_tope_y_difiere_lo_justo(self):
        nuevas = ofertas(150, True, "jobsora") + ofertas(3, False, "colegio")
        a, dif, desc = V.repartir(nuevas, 10, 4, 30)
        self.assertEqual([o["id"] for o in a][:3], ["colegio0", "colegio1", "colegio2"])  # primero las fuentes propias
        self.assertEqual(len(a), 7)  # 3 propias + 4 de agregadores
        self.assertEqual(sum(1 for o in a if o["agregador"]), 4)
        self.assertEqual(len(dif), 30)
        self.assertEqual(len(a) + len(dif) + len(desc), 153)
        self.assertFalse({o["id"] for o in a} & {o["id"] for o in dif + desc})

    def test_pocas_nuevas_salen_todas(self):
        a, dif, desc = V.repartir(ofertas(2, True, "j") + ofertas(2, False, "c"), 10, 4, 30)
        self.assertEqual((len(a), len(dif), len(desc)), (4, 0, 0))

    def test_las_propias_nunca_se_quedan_sin_sitio_por_los_agregadores(self):
        a, dif, desc = V.repartir(ofertas(12, False, "c") + ofertas(50, True, "j"), 10, 4, 30)
        self.assertEqual((len(a), sum(1 for o in a if o["agregador"])), (10, 0))


class Jobsora(unittest.TestCase):
    HTML = '''<article class="x" data-href="https://es.jobsora.com/oferta-111?source=1" data-target="_blank"><h2 class="c-job-item__title"><a href="#">Educador/A Físico Zambrana</a></h2>
    <div class="c-job-item__info-item">Macrosad</div><div class="c-job-item__info-item">Álava</div><p class="c-job-item__description u-text">Profesional en Educación Física para servicios de mayores</p></article>
    <article class="x" data-href="https://es.jobsora.com/oferta-222?source=1"><h2 class="c-job-item__title"><a href="#">Profesor De Física Y Matemáticas</a></h2>
    <div class="c-job-item__info-item">Colegio San José</div><div class="c-job-item__info-item">Madrid</div><p class="c-job-item__description">Se busca docente</p></article>'''

    def test_el_titulo_es_solo_el_puesto_y_el_resto_va_aparte(self):
        with mock.patch.object(F, "get", return_value=self.HTML):
            r = F.jobsora("profesor", "madrid")
        self.assertEqual([o["titulo"] for o in r], ["Educador/a Físico Zambrana", "Profesor de Física y Matemáticas"])
        self.assertEqual(r[0]["empresa"], "Macrosad")
        self.assertEqual(r[0]["lugar"], "Álava")
        self.assertEqual(r[0]["origen"], "Jobsora")  # sin la región
        self.assertNotIn("Macrosad", r[0]["titulo"])

    def test_fisica_y_matematicas_no_es_educacion_fisica(self):
        self.assertNotIn("Educación Física", C.temas("Profesor de Física y Matemáticas"))
        self.assertIn("Educación Física", C.temas("Profesor/a de Educación Física"))

    def test_los_que_no_son_docencia_se_descartan(self):
        with mock.patch.object(F, "get", return_value=self.HTML):
            r = F.jobsora("profesor", "madrid")
        self.assertFalse(V.es_valida_agregador({**r[0], "agregador": True}))  # Macrosad: cuidado de mayores
        self.assertTrue(V.es_valida_agregador({**r[1], "agregador": True}))


class Clasificacion(unittest.TestCase):
    def test_bilingue_e_ingles_requisito_no_son_idiomas(self):
        self.assertEqual(C.temas("Profesor de Educación Secundaria Obligatoria Colegio Bilingüe"), ["Secundaria"])
        self.assertEqual(C.temas("Profesor de Matemáticas, Física y Computer Science (Inglés C1)"), ["Secundaria"])
        self.assertIn("Idiomas", C.temas("Profesor de Inglés"))

    def test_clases_particulares_de_cronoshare_y_academias_no_son_docencia_de_centro(self):
        for titulo, empresa in [("Profesor/a de tenis en Almería — Cronoshare.com", ""), ("Profesor/a de natación en Barcelona", "Cronoshare.com"),
                                ("Profesor/a de Teatro – Coslada", "Antares Danza SL"), ("Profesor/a de Bailes Latinos", "Pebetero S.L."),
                                ("PROFESOR REFUERZO DE INGLÉS VALLECAS", "CULTURAL ACTEX")]:
            self.assertTrue(C.no_docente_agregador(titulo, empresa), titulo)
        for titulo in ["Maestro/a de Educación Física", "Profesor/a de matemáticas ESO/Bachillerato. SUSTITUCIÓN", "Profesor/a de Música", "Bolsa de sustituciones Maestro/a"]:
            self.assertFalse(C.no_docente_agregador(titulo), titulo)

    def test_provincias_cortas_y_leon_xiii(self):
        self.assertEqual(C.comunidad_y_provincia("Maestros de Educación Infantil Lugo"), ("GAL", "Lugo"))
        self.assertEqual(C.comunidad_y_provincia("Profesor en Jaén"), ("AND", "Jaén"))
        self.assertNotEqual(C.comunidad_y_provincia("Colegio León XIII Madrid")[1], "León")


class FlujoCompleto(unittest.TestCase):
    """main() con 150 ofertas de agregadores nuevas: no puede publicar 150."""

    def test_una_avalancha_no_inunda_y_lo_diferido_sigue_sin_ver(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            vistos = d / "vp.json"; vistos.write_text("[]")
            priv = d / "v.json"; priv.write_text("[]")
            fuente = [("jobsora", lambda: ofertas(150, True, "jobsora"), {"agregador": True})]
            salida = []
            with mock.patch.object(V, "VISTOS_PUB", vistos), mock.patch.object(V, "VISTOS_PRIV", priv), mock.patch.object(V, "LIMITES_F", d / "l.json"), \
                 mock.patch.object(V, "LOG_F", d / "p.json"), mock.patch.object(V, "SALUD_F", d / "s.json"), mock.patch.object(calidad, "F", d / "c.json"), mock.patch.object(V, "construir_fuentes", return_value=fuente), \
                 mock.patch.object(V, "es_docente", return_value=True), mock.patch.object(horario, "en_horario", return_value=True), mock.patch.object(V.time, "sleep"), mock.patch("builtins.print", side_effect=lambda *a, **k: salida.append(" ".join(map(str, a)))), \
                 mock.patch.dict(os.environ, {}, clear=True):
                V.main()
            texto = "\n".join(salida)
            self.assertIn("[reparto] 150 nuevas: 4 ahora, 30 para próximas pasadas, 116 descartadas", texto)
            vistas = set(json.loads(vistos.read_text()))
            self.assertEqual(len(vistas), 150 - 30)  # las 30 diferidas siguen sin ver; el resto (publicadas + descartadas) cuenta como visto
            anotado = json.loads((d / "c.json").read_text())
            cifras = next(iter(anotado.values()))["fuentes"]["jobsora"]
            self.assertEqual(cifras["leidas"], 150)
            self.assertEqual((cifras["publicadas"], cifras["tope"], cifras["filtradas"]), (4, 146, 0))


class Calidad(unittest.TestCase):
    def test_cuenta_por_fuente_lo_leido_visto_filtrado_publicado_y_retenido(self):
        o = lambda i, f: {"id": i, "titulo": i, "origen": f}
        leidas = [o("a", "Jobsora · madrid"), o("a2", "Jobsora · madrid"), o("b", "Jobsora · galicia"), o("c", "Jobsora · galicia"), o("d", "Jobsora · galicia"), o("e", "Edutalent (toda España)"), o("e", "Edutalent (toda España)")]
        sin_dup = [leidas[0], leidas[2], leidas[3], leidas[4], leidas[5]]  # a2 repetida de a, y la segunda e repetida
        st = calidad.estadisticas(leidas, sin_dup, ids_vistos={"c"}, ids_candidatas={"a", "b", "e"}, ids_publicadas={"a", "e"})
        self.assertEqual(st["Jobsora"], {"leidas": 5, "repetidas": 1, "vistas": 1, "filtradas": 1, "publicadas": 1, "tope": 1})
        self.assertEqual(st["Edutalent"]["publicadas"], 1)
        self.assertEqual(st["Edutalent"]["repetidas"], 1)

    def test_el_resumen_suma_las_ultimas_24_horas_y_avisa_del_ruido(self):
        import datetime
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "c.json"
            ahora = datetime.datetime(2026, 11, 25, 8, 0, tzinfo=datetime.timezone.utc)
            cifras = lambda **k: {**dict.fromkeys(calidad.COLUMNAS, 0), **k}
            calidad.registrar("pesadas", {"Jobsora": cifras(leidas=1200, publicadas=4, tope=6, filtradas=90), "Edutalent": cifras(leidas=60, publicadas=3)}, ahora=ahora - datetime.timedelta(hours=3), ruta=ruta)
            calidad.registrar("ligeras", {"Jobsora": cifras(leidas=0)}, ahora=ahora - datetime.timedelta(hours=2), ruta=ruta)
            calidad.registrar("enlaces", enlaces={"comprobadas": 50, "cerradas": 2, "sin_respuesta": 5}, ahora=ahora - datetime.timedelta(hours=1), ruta=ruta)
            calidad.registrar("pesadas", {"Jobsora": cifras(leidas=9)}, ahora=ahora - datetime.timedelta(hours=30), ruta=ruta)  # fuera de las 24 h
            fuentes, enlaces, pasadas = calidad.resumen_24h(ahora=ahora, ruta=ruta)
            self.assertEqual((pasadas, fuentes["Jobsora"]["leidas"], enlaces["cerradas"]), (2, 1200, 2))
            texto = "\n".join(calidad.lineas_informe(fuentes, enlaces, pasadas))
            for frag in ["Calidad de las fuentes", "Jobsora: leídas 1200 · nuevas 100 · publicadas 4 · filtradas 90 · retenidas por el tope 6", "descartamos el 90 % de sus nuevas",
                         "50 comprobados · 2 marcados como cerrados · 5 sin respuesta", "Edutalent: leídas 60"]:
                self.assertIn(frag, texto)
            self.assertIn("sin datos", "\n".join(calidad.lineas_informe({}, {}, 0)))

    def test_dos_anotaciones_en_el_mismo_minuto_no_se_pisan(self):
        import datetime
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "c.json"
            ahora = datetime.datetime(2026, 11, 25, 8, 30, tzinfo=datetime.timezone.utc)
            calidad.registrar("pesadas", {"X": {**dict.fromkeys(calidad.COLUMNAS, 0), "leidas": 7}}, ahora=ahora, ruta=ruta)
            calidad.registrar("enlaces", enlaces={"comprobadas": 3, "cerradas": 1, "sin_respuesta": 0}, ahora=ahora, ruta=ruta)
            fuentes, enlaces, pasadas = calidad.resumen_24h(ahora=ahora, ruta=ruta)
            self.assertEqual((pasadas, fuentes["X"]["leidas"], enlaces["comprobadas"]), (1, 7, 3))

    def test_se_borra_lo_de_mas_de_3_dias(self):
        import datetime
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "c.json"
            ahora = datetime.datetime(2026, 11, 25, 8, 0, tzinfo=datetime.timezone.utc)
            calidad.registrar("pesadas", {"X": dict.fromkeys(calidad.COLUMNAS, 1)}, ahora=ahora - datetime.timedelta(days=5), ruta=ruta)
            calidad.registrar("pesadas", {"X": dict.fromkeys(calidad.COLUMNAS, 1)}, ahora=ahora, ruta=ruta)
            self.assertEqual(len(json.loads(ruta.read_text())), 1)


class Enlaces(unittest.TestCase):
    def registro(self, **extra):
        return {"t": "Oferta", "u": "https://colegio.es/o/1", "ts": 1_000_000, "m": [[2, 11], [9, 12]], "x": "🏫 Oferta", "estado": "", **extra}

    def test_clasifica_las_respuestas(self):
        self.assertEqual(E.estado_enlace(404, ""), "muerto")
        self.assertEqual(E.estado_enlace(410, ""), "muerto")
        self.assertEqual(E.estado_enlace(200, "<p>Oferta caducada</p>"), "muerto")
        self.assertEqual(E.estado_enlace(200, "Esta oferta ya no está disponible"), "muerto")
        self.assertEqual(E.estado_enlace(200, "Se busca maestro/a de EF"), "vivo")
        for codigo in (0, 403, 429, 500, 503):
            self.assertEqual(E.estado_enlace(codigo, ""), "incierto")  # un bloqueo o un fallo no cierra nada

    def test_se_cierra_solo_tras_dos_comprobaciones_seguidas_y_se_editan_todos_los_mensajes(self):
        log = {"a": self.registro()}
        editados = []
        ahora = 1_000_000 + 86400
        args = dict(ahora=ahora, abrir_fn=lambda u: (404, ""), editar_fn=lambda g, m, t, b: editados.append((m, t, b)), pausa=0)
        r1 = E.comprobar(log, "-100", **args)
        self.assertEqual((r1["cerradas"], log["a"]["estado"], log["a"]["enl"]), (0, "", 1))
        r2 = E.comprobar(log, "-100", **args)
        self.assertEqual((r2["cerradas"], log["a"]["estado"]), (1, "cerrada"))
        self.assertEqual([m for m, _, _ in editados], [11, 12])
        self.assertTrue(all(t.startswith("🔒 CERRADA") and "🏫 Oferta" in t and b == "https://colegio.es/o/1" for _, t, b in editados))
        E.comprobar(log, "-100", **args)  # ya cerrada: no se toca más
        self.assertEqual(len(editados), 2)

    def test_un_fallo_intermedio_o_una_pagina_viva_reinicia_la_cuenta(self):
        log = {"a": self.registro()}
        respuestas = iter([(404, ""), (200, "Maestro de EF"), (404, ""), (403, "")])
        args = dict(ahora=1_000_000 + 86400, abrir_fn=lambda u: next(respuestas), editar_fn=lambda *a: None, pausa=0)
        for _ in range(4):
            E.comprobar(log, "-100", **args)
        self.assertEqual((log["a"]["estado"], log["a"]["enl"]), ("", 1))  # 404, vivo (reinicia), 404, 403 (no cuenta)

    def test_ignora_las_antiguas_las_ya_cerradas_y_las_sin_enlace(self):
        log = {"vieja": self.registro(ts=1_000_000), "cerrada": self.registro(estado="cerrada"), "borrada": self.registro(estado="borrada"), "sin": self.registro(u="")}
        llamadas = []
        r = E.comprobar(log, "-100", ahora=1_000_000 + 40 * 86400, abrir_fn=lambda u: llamadas.append(u) or (404, ""), editar_fn=lambda *a: None, pausa=0)
        self.assertEqual((r["comprobadas"], llamadas), (0, []))


class Horario(unittest.TestCase):
    def hora(self, y, m, d, h, mi=0, utc=False):
        import datetime
        tz = datetime.timezone.utc if utc else horario.MADRID
        return datetime.datetime(y, m, d, h, mi, tzinfo=tz)

    def test_solo_de_9_a_21_en_hora_de_madrid(self):
        for h in (9, 12, 20):
            self.assertTrue(horario.en_horario(self.hora(2026, 11, 25, h, 30)), h)
        self.assertTrue(horario.en_horario(self.hora(2026, 11, 25, 20, 59)))
        for h in (0, 3, 6, 8, 21, 22, 23):
            self.assertFalse(horario.en_horario(self.hora(2026, 11, 25, h, 10)), h)
        self.assertFalse(horario.en_horario(self.hora(2026, 11, 25, 8, 59)))

    def test_la_hora_es_la_de_madrid_en_invierno_y_en_verano(self):
        # invierno: 08:10 UTC = 09:10 Madrid (dentro); 20:10 UTC = 21:10 Madrid (fuera)
        self.assertTrue(horario.en_horario(self.hora(2026, 11, 25, 8, 10, utc=True)))
        self.assertFalse(horario.en_horario(self.hora(2026, 11, 25, 20, 10, utc=True)))
        # verano: 07:10 UTC = 09:10 Madrid (dentro); 08:10 UTC = 10:10; 19:10 UTC = 21:10 Madrid (fuera); 06:10 UTC = 08:10 Madrid (fuera)
        self.assertTrue(horario.en_horario(self.hora(2026, 7, 15, 7, 10, utc=True)))
        self.assertFalse(horario.en_horario(self.hora(2026, 7, 15, 19, 10, utc=True)))
        self.assertFalse(horario.en_horario(self.hora(2026, 7, 15, 6, 10, utc=True)))

    def test_de_noche_el_vigilante_no_lee_ni_manda_nada(self):
        with mock.patch.object(horario, "en_horario", return_value=False), mock.patch.object(V, "construir_fuentes", side_effect=AssertionError("no debe leer fuentes")), \
             mock.patch.object(V, "telegram", side_effect=AssertionError("no debe mandar nada")), mock.patch("sys.argv", ["vigilante.py", "pesadas"]):
            V.main()  # no lanza excepciones: sale sin hacer nada

    def test_el_volcado_manual_se_salta_el_horario(self):
        with mock.patch.object(horario, "en_horario", return_value=False), mock.patch.object(V, "construir_fuentes", return_value=[]) as c, mock.patch("sys.argv", ["vigilante.py", "ligeras", "--volcado", "5"]), \
             mock.patch.object(V, "VISTOS_PUB", Path(tempfile.mkdtemp()) / "vp.json"), mock.patch.object(V, "VISTOS_PRIV", Path(tempfile.mkdtemp()) / "v.json"), mock.patch.dict(os.environ, {}, clear=True):
            V.main()
        c.assert_called_once()


class TemasDelGrupo(unittest.TestCase):
    def destino(self, titulo):
        return V.temas_destino(titulo, C.temas(titulo))

    def test_cada_oferta_va_a_su_etapa(self):
        casos = {
            "Maestro/a de Educación Infantil": ["Infantil"],
            "Educador/a infantil 0-3 años": ["Infantil"],
            "Maestro/a de Primaria": ["Primaria"],
            "Maestro/a de Educación Física": ["Primaria"],  # «maestro/a» sin etapa cuenta como Primaria
            "Profesor/a de Matemáticas ESO y Bachillerato": ["Secundaria y Bachillerato"],
            "Profesor de Educación Secundaria Obligatoria": ["Secundaria y Bachillerato"],
            "Docente Ciclo Formativo de Informática": ["FP"],
            "Profesor/a de FP Administración": ["FP"],
            "Maestro/a de Infantil y Primaria": ["Infantil", "Primaria"],
        }
        for titulo, esperado in casos.items():
            self.assertEqual(self.destino(titulo), esperado, titulo)

    def test_pt_al_educacion_especial_y_orientacion_van_a_apoyo_sea_cual_sea_la_etapa(self):
        for titulo in ["Maestro/a de Primaria con mención en Audición y Lenguaje", "Maestra Infantil y Primaria - Pedagogía Terapéutica", "Maestro/a de PT",
                       "Logopeda en colegio", "Orientador/a educativo", "Maestro/a de Educación Especial"]:
            self.assertEqual(self.destino(titulo), ["Apoyo y orientación"], titulo)

    def test_sin_etapa_va_a_otras_ofertas_y_nunca_a_un_tema_que_no_existe(self):
        for titulo in ["Profesor/a de Inglés", "Profesor/a de Música", "Profesor de Religión", "Profesor/a de Yoga"]:
            self.assertEqual(self.destino(titulo), ["Otras ofertas"], titulo)
        todos = {d for t in ["Maestro/a de Primaria", "Profesor/a de Inglés", "Logopeda", "Docente FP", "Maestro/a Infantil", "Profesor ESO"] for d in self.destino(t)}
        self.assertTrue(todos <= set(C.TEMAS_GRUPO))
        import json as j
        topics = j.loads((Path(__file__).parent / "topics.json").read_text())
        self.assertEqual(set(topics), set(C.TEMAS_GRUPO))  # cada tema del grupo tiene su hilo en topics.json

    def test_como_mucho_dos_temas_por_oferta(self):
        self.assertLessEqual(len(self.destino("Maestro/a Infantil, Primaria y Secundaria")), 2)


if __name__ == "__main__":
    unittest.main()
