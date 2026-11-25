"""Pruebas del vigilante (sin red). Uso: python3 -m unittest -v test_vigilante"""
import json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

import clasificar as C
import fuentes as F
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
                 mock.patch.object(V, "LOG_F", d / "p.json"), mock.patch.object(V, "SALUD_F", d / "s.json"), mock.patch.object(V, "construir_fuentes", return_value=fuente), \
                 mock.patch.object(V, "es_docente", return_value=True), mock.patch.object(V.time, "sleep"), mock.patch("builtins.print", side_effect=lambda *a, **k: salida.append(" ".join(map(str, a)))), \
                 mock.patch.dict(os.environ, {}, clear=True):
                V.main()
            texto = "\n".join(salida)
            self.assertIn("[reparto] 150 nuevas: 4 ahora, 30 para próximas pasadas, 116 descartadas", texto)
            vistas = set(json.loads(vistos.read_text()))
            self.assertEqual(len(vistas), 150 - 30)  # las 30 diferidas siguen sin ver; el resto (publicadas + descartadas) cuenta como visto


if __name__ == "__main__":
    unittest.main()
