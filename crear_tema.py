#!/usr/bin/env python3
"""Crea el tema «Instagram» del grupo (un solo uso)."""
import json, os, urllib.error, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/createForumTopic", data=urllib.parse.urlencode({"chat_id": GRUPO, "name": "Instagram"}).encode())
try:
    r = json.load(urllib.request.urlopen(req, timeout=30))
except urllib.error.HTTPError as e:
    r = json.load(e)
print("TEMA", r.get("ok"), r.get("result", {}).get("message_thread_id"), r.get("description", ""))
