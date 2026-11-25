"""Horario de envío: solo se manda algo de 9:00 a 21:00 (hora de Madrid). De noche no se molesta a nadie.

Afecta a todo lo que el vigilante manda por su cuenta: las ofertas del grupo, los avisos a los suscriptores del bot y el resumen diario del grupo.
Fuera de ese horario el vigilante ni siquiera lee las fuentes: lo que aparezca por la noche se publicará (con el tope de siempre) a partir de las 9:00.
Para pruebas y ejecuciones manuales: FUERA_DE_HORARIO=1 lo salta.
"""
import datetime, os
from zoneinfo import ZoneInfo

INICIO, FIN = 9, 21  # de 9:00 a 21:00 (se manda desde las 9:00 y hasta las 20:59)
MADRID = ZoneInfo("Europe/Madrid")


def en_horario(ahora=None):
    if os.environ.get("FUERA_DE_HORARIO") == "1":
        return True
    ahora = ahora.astimezone(MADRID) if ahora else datetime.datetime.now(MADRID)
    return INICIO <= ahora.hour < FIN
