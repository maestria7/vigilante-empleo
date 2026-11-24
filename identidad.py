#!/usr/bin/env python3
"""Cambia el nombre y la foto del grupo (un solo uso, desde GitHub Actions)."""
import json, os, urllib.parse, urllib.request, uuid

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
URL = f"https://api.telegram.org/bot{TOK}/"


def llamar(metodo, datos, fichero=None):
    if fichero:
        b = uuid.uuid4().hex
        cuerpo = b""
        for k, v in datos.items():
            cuerpo += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        cuerpo += f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="f.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
        cuerpo += open(fichero, "rb").read() + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(URL + metodo, data=cuerpo, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    else:
        req = urllib.request.Request(URL + metodo, data=urllib.parse.urlencode(datos).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        return json.load(e)


r = llamar("setChatTitle", {"chat_id": GRUPO, "title": "Radar Docente by Maestría · Vacantes"})
print("TITULO", r.get("ok"), r.get("description", ""))
r = llamar("setChatPhoto", {"chat_id": GRUPO}, "radar_avatar.jpg")
print("FOTO", r.get("ok"), r.get("description", ""))
