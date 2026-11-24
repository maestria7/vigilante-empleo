#!/usr/bin/env python3
"""Cierra la escritura de los miembros en el grupo (solo el bot y los administradores publican)."""
import json, os, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


print("ANTES", json.dumps(api("getChat", chat_id=GRUPO).get("result", {}).get("permissions")))
yo = api("getChatMember", chat_id=GRUPO, user_id=api("getMe")["result"]["id"]).get("result", {})
print("BOT admin:", yo.get("status"), "puede restringir:", yo.get("can_restrict_members"))
permisos = {k: False for k in ("can_send_messages", "can_send_audios", "can_send_documents", "can_send_photos", "can_send_videos",
                               "can_send_video_notes", "can_send_voice_notes", "can_send_polls", "can_send_other_messages",
                               "can_add_web_page_previews", "can_change_info", "can_pin_messages", "can_manage_topics")}
permisos["can_invite_users"] = True
r = api("setChatPermissions", chat_id=GRUPO, permissions=json.dumps(permisos), use_independent_chat_permissions="true")
print("RESULTADO", r.get("ok"), r.get("description", ""))
print("DESPUES", json.dumps(api("getChat", chat_id=GRUPO).get("result", {}).get("permissions")))
