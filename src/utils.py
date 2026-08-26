import logging
import time
import re
import requests
import json
from typing import Union, Optional
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Configura el logging básico."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

def send_safe_message(
    bot: telebot.TeleBot,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> Optional[telebot.types.Message]:
    """
    Envía un mensaje dividiéndolo en partes si excede los 4096 caracteres.
    """
    if not text:
        return None
    max_len = 4000
    if len(text) <= max_len:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    # Dividir por párrafos o saltos de línea
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            parts.append(current)
            current = line
        else:
            current += "\n" + line if current else line
    if current:
        parts.append(current)
    
    last_msg = None
    for i, part in enumerate(parts):
        markup = reply_markup if i == len(parts) - 1 else None
        last_msg = bot.send_message(chat_id, part, reply_markup=markup, parse_mode=parse_mode)
    return last_msg

def calcular_diferencia_horaria(HoraHost: float = None, devolver: str = "hora_host"):
    """
    Calcula la diferencia horaria entre el host y Lima (Perú).
    devolver: 'diferencia_host', 'hora_host', 'hora_peru', 'peru'
    """
    if HoraHost is None:
        HoraHost = time.time()
    try:
        # Obtener timestamp de Lima desde API
        resp = requests.get("http://api.timezonedb.com/v2.1/get-time-zone",
                            params={"key": "68TYQMUQ25P6", "by": "zone", "format": "json", "zone": "America/Lima"},
                            timeout=5)
        data = resp.json()
        lima = data["timestamp"]
    except Exception:
        # Fallback: usar diferencia fija de 5 horas (UTC-5)
        lima = time.time() - 18000
    
    if devolver == "diferencia_host":
        return lima - time.time()
    elif devolver == "hora_host":
        return time.mktime(time.localtime(HoraHost + (lima - time.time())))
    elif devolver == "hora_peru":
        return time.mktime(time.localtime(lima + (HoraHost - time.time())))
    elif devolver == "peru":
        return time.mktime(time.localtime(lima))
    else:
        return HoraHost

def comprobar_canales(bot: telebot.TeleBot, db, admin_id: int) -> Optional[str]:
    """
    Verifica que el bot tenga permisos en todos los canales registrados.
    Para canales: exige ser administrador con can_post_messages.
    Para grupos: solo exige ser miembro.
    Retorna un mensaje de error si hay problemas, o None si todo bien.
    """
    channels = db.get_channels()
    if not channels:
        return None
    
    err_msg = "❗Atención❗\nLos siguientes chats han sido eliminados por problemas de permisos:\n\n"
    any_error = False
    
    for chat_id, nombre in channels:
        try:
            chat = bot.get_chat(chat_id)
            member = bot.get_chat_member(chat_id, bot.user.id)
            
            if chat.type == "channel":
                # Canal: necesita ser administrador con permiso de publicar
                if member.status != "administrator":
                    err_msg += f"- {nombre} (canal) ⛔ No soy administrador\n"
                    db.remove_channel(chat_id)
                    any_error = True
                    continue
                if not member.can_post_messages:
                    err_msg += f"- {nombre} (canal) ⛔ No tengo permiso para publicar\n"
                    db.remove_channel(chat_id)
                    any_error = True
                    continue
            else:
                # Grupo/Supergrupo: solo necesita ser miembro
                if member.status not in ["member", "administrator", "creator"]:
                    err_msg += f"- {nombre} (grupo) ⛔ No soy miembro\n"
                    db.remove_channel(chat_id)
                    any_error = True
                    continue
        except Exception as e:
            err_msg += f"- {nombre} ⛔ Chat inaccesible o ya no existe\n"
            db.remove_channel(chat_id)
            any_error = True
    
    return err_msg if any_error else None