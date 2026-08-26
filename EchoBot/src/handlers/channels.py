import logging
import re
import os
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from src.utils import send_safe_message, comprobar_canales
from src.persistence import Persistence

logger = logging.getLogger(__name__)

# Almacenamiento temporal para selecciones (por usuario)
temp_data = {}

def handle_channel_callback(bot, config, db, publications, scheduler, persistence, call):
    """Maneja callbacks relacionados con canales."""
    data = call.data
    user_id = call.from_user.id

    if data == "lista_canales_elegir":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("👁 Mis Canales", callback_data="ver_canal_search:0"),
            InlineKeyboardButton("➕Añadir Canal", callback_data="anadir_canal"),
            InlineKeyboardButton("❌Eliminar Canal", callback_data="eliminar_canal"),
            InlineKeyboardButton("Volver | Menú ♻", callback_data="volver_menu")
        )
        send_safe_message(bot, call.message.chat.id, "👇 Elija una opción:", reply_markup=markup)
        return

    if data == "anadir_canal":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(
            call.message.chat.id,
            "Envía los canales o grupos (ID o @username) separados por comas.\n"
            "Ejemplo: @canal1, -100123456, @grupo_ventas\n"
            "Para CANALES: el bot debe ser administrador con permisos de publicar.\n"
            "Para GRUPOS: el bot solo necesita ser miembro (a menos que el grupo restrinja a solo admins).",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_add_channels, bot, config, db, publications, call)
        return

    if data.startswith("ver_canal_search:"):
        index = int(data.split(":")[1])
        show_channels(bot, db, call, index)
        return

    if data.startswith("ver_canal:"):
        chat_id = int(data.split(":")[1])
        try:
            chat = bot.get_chat(chat_id)
            info = f"Nombre: {chat.title}\nTipo: {chat.type}\nMiembros: {bot.get_chat_member_count(chat_id)}"
            bot.answer_callback_query(call.id, info, show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)
        return

    if data == "eliminar_canal":
        temp_data[user_id] = {"selected": [], "page": 0}
        show_delete_channels(bot, db, call, 0)
        return

    if data.startswith("eliminar_canal_"):
        handle_delete_channel_callbacks(bot, config, db, publications, scheduler, persistence, call)
        return

def process_add_channels(message, bot, config, db, publications, call):
    """Procesa el mensaje con la lista de canales/grupos a añadir."""
    if message.text is None:
        return
    text = message.text.strip()
    if not text:
        bot.send_message(message.chat.id, "No ingresaste nada.")
        return

    channels = [ch.strip() for ch in text.split(",") if ch.strip()]
    added = 0
    errors = []

    for ch in channels:
        # Limpiar formato
        if ch.isdigit() or ch.startswith("-"):
            chat_id = int(ch)
        elif "t.me/" in ch:
            chat_id = "@" + ch.split("/")[-1]
        elif not ch.startswith("@"):
            chat_id = "@" + ch
        else:
            chat_id = ch

        try:
            chat = bot.get_chat(chat_id)
            member = bot.get_chat_member(chat.id, bot.user.id)
            
            # Determinar si es canal o grupo
            if chat.type == "channel":
                # Para canales: necesita ser administrador con permiso de publicar
                if member.status != "administrator":
                    errors.append(f"{chat.title}: No soy administrador del canal")
                    continue
                if not member.can_post_messages:
                    errors.append(f"{chat.title}: No tengo permiso para publicar en el canal")
                    continue
            else:
                # Para grupos/supergrupos: solo necesita ser miembro
                if member.status not in ["member", "administrator", "creator"]:
                    errors.append(f"{chat.title}: No soy miembro del grupo")
                    continue
                # Si el grupo está restringido a solo admins, lo detectaremos al enviar
                # pero no lo bloqueamos aquí.
            
            # Agregar a la base de datos
            if db.add_channel(chat.id, chat.title):
                added += 1
            else:
                errors.append(f"{chat.title}: Ya existe en la base de datos")
        except Exception as e:
            errors.append(f"{ch}: {e}")

    msg = f"Se agregaron {added} canales/grupos."
    if errors:
        msg += "\n\nErrores:\n" + "\n".join(errors)
    send_safe_message(
        bot, message.chat.id, msg,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="lista_canales_elegir")]])
    )

def show_channels(bot, db, call, index):
    """Muestra una página de canales registrados."""
    channels = db.get_channels()
    if not channels:
        send_safe_message(
            bot, call.message.chat.id,
            "No hay canales/grupos registrados.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Añadir", callback_data="anadir_canal")]])
        )
        return

    page_size = 10
    total = len(channels)
    start = index
    end = min(start + page_size, total)
    page_channels = channels[start:end]

    text = "📋 Lista de canales/grupos:\n\n"
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    markup = InlineKeyboardMarkup(row_width=5)
    for i, (cid, name) in enumerate(page_channels):
        text += f"{emojis[i]} {name} (ID: {cid})\n"
        markup.add(InlineKeyboardButton(emojis[i], callback_data=f"ver_canal:{cid}"))

    text += f"\nMostrando {start+1}-{end} de {total}"
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"ver_canal_search:{start-page_size}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"ver_canal_search:{end}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("Volver", callback_data="lista_canales_elegir"))

    send_safe_message(bot, call.message.chat.id, text, reply_markup=markup)

def show_delete_channels(bot, db, call, page):
    """Muestra canales/grupos para seleccionar y eliminar."""
    channels = db.get_channels()
    if not channels:
        send_safe_message(bot, call.message.chat.id, "No hay canales/grupos para eliminar.")
        return

    user_id = call.from_user.id
    selected = temp_data.get(user_id, {}).get("selected", [])
    page_size = 6
    total = len(channels)
    start = page
    end = min(start + page_size, total)
    page_channels = channels[start:end]

    markup = InlineKeyboardMarkup(row_width=1)
    for cid, name in page_channels:
        is_selected = cid in selected
        btn_text = f"✅ {name}" if is_selected else name
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"eliminar_canal_toggle:{cid}:{page}"))

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"eliminar_canal_page:{start-page_size}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"eliminar_canal_page:{end}"))
    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("✅ Confirmar eliminación", callback_data="eliminar_canal_confirm"))
    markup.add(InlineKeyboardButton("Volver", callback_data="lista_canales_elegir"))

    send_safe_message(bot, call.message.chat.id, "Selecciona los elementos a eliminar:", reply_markup=markup)

def handle_delete_channel_callbacks(bot, config, db, publications, scheduler, persistence, call):
    """Maneja toggles, paginación y confirmación de eliminación."""
    data = call.data
    user_id = call.from_user.id
    if user_id not in temp_data:
        temp_data[user_id] = {"selected": [], "page": 0}

    if data.startswith("eliminar_canal_toggle:"):
        parts = data.split(":")
        cid = int(parts[1])
        page = int(parts[2])
        selected = temp_data[user_id]["selected"]
        if cid in selected:
            selected.remove(cid)
        else:
            selected.append(cid)
        temp_data[user_id]["selected"] = selected
        show_delete_channels(bot, db, call, page)
        return

    if data.startswith("eliminar_canal_page:"):
        page = int(data.split(":")[1])
        show_delete_channels(bot, db, call, page)
        return

    if data == "eliminar_canal_confirm":
        selected = temp_data.get(user_id, {}).get("selected", [])
        if not selected:
            bot.answer_callback_query(call.id, "No has seleccionado ningún elemento.")
            return
        # Eliminar de DB
        for cid in selected:
            db.remove_channel(cid)
            # Eliminar también de las publicaciones
            for pub in publications.values():
                if cid in pub.canales:
                    pub.canales.remove(cid)
        # Guardar cambios
        persistence.save(publications)
        temp_data[user_id]["selected"] = []
        send_safe_message(bot, call.message.chat.id, f"Se eliminaron {len(selected)} elementos.")
        # Volver al menú de canales
        handle_channel_callback(bot, config, db, publications, scheduler, persistence, call)
        return