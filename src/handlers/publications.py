import logging
import re
import os
import time
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from src.models import Publicacion
from src.utils import send_safe_message, comprobar_canales
from src.publisher import Publisher

logger = logging.getLogger(__name__)

# Almacenamiento temporal para flujos paso a paso
temp_data = {}

def handle_publication_callback(bot, config, db, publications, scheduler, persistence, call):
    """Maneja callbacks relacionados con publicaciones."""
    data = call.data
    user_id = call.from_user.id

    if data == "publicacion":
        start_create_publication(bot, config, db, publications, call)
        return

    if data.startswith("ver_publicaciones"):
        handle_view_publications(bot, config, db, publications, scheduler, persistence, call)
        return

    if data.startswith("operacion_") or data.startswith("publicacion/c"):
        handle_publication_channels_operations(bot, config, db, publications, call)
        return

    # Otros
    bot.answer_callback_query(call.id, "Opción no disponible")

# ---------- CREACIÓN DE PUBLICACIÓN ----------
def start_create_publication(bot, config, db, publications, call):
    """Inicia el proceso de creación de una nueva publicación."""
    channels = db.get_channels()
    if not channels:
        send_safe_message(
            bot, call.message.chat.id,
            "No hay canales registrados. Agrega algunos primero.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Añadir Canal", callback_data="anadir_canal")]])
        )
        return

    user_id = call.from_user.id
    temp_data[user_id] = {"selected_channels": [], "step": "select_channels"}
    show_channel_selection_for_publication(bot, db, call, 0, user_id)

def show_channel_selection_for_publication(bot, db, call, page, user_id):
    """Muestra lista de canales para seleccionar en la publicación."""
    channels = db.get_channels()
    page_size = 6
    start = page
    end = min(start + page_size, len(channels))
    page_channels = channels[start:end]

    selected = temp_data.get(user_id, {}).get("selected_channels", [])
    markup = InlineKeyboardMarkup(row_width=1)
    for cid, name in page_channels:
        is_sel = cid in selected
        markup.add(InlineKeyboardButton(f"✅ {name}" if is_sel else name, callback_data=f"pub_ch_toggle:{cid}:{page}"))

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"pub_ch_page:{start-page_size}"))
    if end < len(channels):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"pub_ch_page:{end}"))
    if nav:
        markup.row(*nav)
    markup.add(InlineKeyboardButton("✅ Listo", callback_data="pub_ch_confirm"))
    markup.add(InlineKeyboardButton("Cancelar", callback_data="volver_menu"))

    send_safe_message(bot, call.message.chat.id, "Selecciona los canales para esta publicación:", reply_markup=markup)

def handle_publication_channels_operations(bot, config, db, publications, call):
    """Maneja toggles, paginación y confirmación de selección de canales para publicación."""
    data = call.data
    user_id = call.from_user.id

    if data.startswith("pub_ch_toggle:"):
        parts = data.split(":")
        cid = int(parts[1])
        page = int(parts[2])
        selected = temp_data.get(user_id, {}).get("selected_channels", [])
        if cid in selected:
            selected.remove(cid)
        else:
            selected.append(cid)
        temp_data[user_id]["selected_channels"] = selected
        show_channel_selection_for_publication(bot, db, call, page, user_id)
        return

    if data.startswith("pub_ch_page:"):
        page = int(data.split(":")[1])
        show_channel_selection_for_publication(bot, db, call, page, user_id)
        return

    if data == "pub_ch_confirm":
        selected = temp_data.get(user_id, {}).get("selected_channels", [])
        if not selected:
            bot.answer_callback_query(call.id, "Debes seleccionar al menos un canal.")
            return
        temp_data[user_id]["channels"] = selected
        temp_data[user_id]["step"] = "content"
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(
            call.message.chat.id,
            "Ahora envía el contenido de la publicación.\n"
            "Puedes usar formato:\n"
            "{{n}}texto{{n}} -> negrita\n"
            "{{s}}texto{{s}} -> subrayado\n"
            "{{i}}texto{{i}} -> cursiva\n"
            "{{m}}texto{{m}} -> monoespaciado\n"
            "{{b}}%Texto%&URL&{{b}} -> botón\n\n"
            "También puedes adjuntar un archivo (foto, video, audio, documento).\n"
            "Luego de enviarlo, especificarás el intervalo en minutos.",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_publication_content, bot, config, db, publications, call)
        return

def process_publication_content(message, bot, config, db, publications, call):
    """Procesa el contenido de la publicación (texto y/o multimedia)."""
    user_id = call.from_user.id
    channels = temp_data.get(user_id, {}).get("channels", [])
    if not channels:
        bot.send_message(message.chat.id, "No hay canales seleccionados. Reinicia el proceso.")
        return

    texto = ""
    multimedia = None
    if message.content_type == "text":
        texto = message.text
    elif message.content_type in ["photo", "video", "audio", "document", "voice"]:
        file_id = None
        file_type = message.content_type
        if file_type == "photo":
            file_id = message.photo[-1].file_id
        else:
            file_id = getattr(message, file_type).file_id
        file_info = bot.get_file(file_id)
        ext = os.path.splitext(file_info.file_path)[1] or ".bin"
        media_dir = config.MEDIA_DIR
        os.makedirs(media_dir, exist_ok=True)
        nombre = f"{int(time.time())}_{random.randint(1000,9999)}{ext}"
        ruta = os.path.join(media_dir, nombre)
        with open(ruta, "wb") as f:
            f.write(bot.download_file(file_info.file_path))
        multimedia = [ruta, file_type]
        texto = message.caption or ""
    else:
        bot.send_message(message.chat.id, "Tipo de archivo no soportado. Intenta de nuevo.")
        return

    temp_data[user_id]["texto"] = texto
    temp_data[user_id]["multimedia"] = multimedia
    msg = bot.send_message(
        message.chat.id,
        "Ahora ingresa el intervalo de publicación en MINUTOS (ej: 120 para 2 horas).\n"
        "Si quieres que solo se publique una vez, escribe 0."
    )
    bot.register_next_step_handler(msg, process_publication_interval, bot, config, db, publications, call)

def process_publication_interval(message, bot, config, db, publications, call):
    """Procesa el intervalo y finaliza creación de la publicación."""
    user_id = call.from_user.id
    try:
        interval_min = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Debe ser un número entero. Reinicia el proceso.")
        return

    channels = temp_data.get(user_id, {}).get("channels", [])
    texto = temp_data.get(user_id, {}).get("texto", "")
    multimedia = temp_data.get(user_id, {}).get("multimedia", None)
    if not channels:
        bot.send_message(message.chat.id, "No hay canales. Reinicia.")
        return

    # Parsear markup (botones)
    markup = None
    if "{{b}}" in texto:
        markup = InlineKeyboardMarkup()
        matches = re.findall(r"{{b}}%([^%]+)%&([^&]+)&{{b}}", texto)
        for btn_text, url in matches:
            markup.add(InlineKeyboardButton(btn_text, url=url))
        texto = re.sub(r"{{b}}%[^%]+%&[^&]+&{{b}}", "", texto)

    # Generar ID y nombre
    nombre = f"Objeto_{len(publications)+1}_{random.randint(100,999)}"
    id_pub = str(len(publications)+1)

    pub = Publicacion(
        ID=id_pub,
        texto=texto,
        canales=channels,
        tiempo_publicacion=interval_min * 60 if interval_min > 0 else 0,
        nombre=nombre,
        multimedia=multimedia,
        markup=markup
    )
    publications[nombre] = pub
    persistence.save(publications)

    temp_data[user_id] = {}
    send_safe_message(
        bot, message.chat.id,
        f"Publicación creada con ID: {id_pub}\nIntervalo: {interval_min} minutos.\nUsa /panel para gestionarla.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver al panel", callback_data="volver_menu")]])
    )

# ---------- VER / GESTIONAR PUBLICACIONES ----------
def handle_view_publications(bot, config, db, publications, scheduler, persistence, call):
    """Maneja la visualización, edición y eliminación de publicaciones."""
    data = call.data
    user_id = call.from_user.id

    if data == "ver_publicaciones" or data.startswith("ver_publicaciones_search:"):
        # Mostrar lista paginada
        page = 0
        if ":" in data:
            page = int(data.split(":")[1])
        show_publications_list(bot, config, db, publications, scheduler, persistence, call, page)
        return

    if data.startswith("ver_publicaciones_index:"):
        # Ver detalle de una publicación
        pub_name = data.split(":", 1)[1]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "La publicación ya no existe.")
            return
        show_publication_detail(bot, config, db, publications, scheduler, persistence, call, pub_name)
        return

    if data.startswith("ver_publicaciones/del:"):
        # Eliminar publicación
        pub_name = data.split(":", 1)[1]
        if pub_name in publications:
            # Eliminar archivos multimedia si existen
            pub = publications[pub_name]
            if pub.multimedia and os.path.exists(pub.multimedia[0]):
                try:
                    os.remove(pub.multimedia[0])
                except:
                    pass
            del publications[pub_name]
            persistence.save(publications)
            bot.answer_callback_query(call.id, "Publicación eliminada.")
            # Volver a la lista
            show_publications_list(bot, config, db, publications, scheduler, persistence, call, 0)
        else:
            bot.answer_callback_query(call.id, "La publicación ya no existe.")
        return

    if data.startswith("ver_publicaciones/send:"):
        # Enviar publicación ahora
        pub_name = data.split(":", 1)[1]
        if pub_name in publications:
            publisher = Publisher()
            publisher.send_publication(publications[pub_name], db, bot)
            bot.answer_callback_query(call.id, "Publicación enviada.")
        else:
            bot.answer_callback_query(call.id, "La publicación ya no existe.")
        return

    if data.startswith("ver_publicaciones/time_to_post:"):
        # Programar hora específica
        pub_name = data.split(":", 1)[1]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "La publicación ya no existe.")
            return
        ask_for_time(bot, call, pub_name)
        return

    if data.startswith("ver_publicaciones/change_time:"):
        # Cambiar intervalo
        pub_name = data.split(":", 1)[1]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "La publicación ya no existe.")
            return
        ask_for_new_interval(bot, call, pub_name)
        return

    # Gestión de canales de una publicación (añadir/eliminar)
    if data.startswith("ver_publicaciones/cc/"):
        handle_publication_channel_management(bot, config, db, publications, call)
        return

def show_publications_list(bot, config, db, publications, scheduler, persistence, call, page):
    """Muestra lista paginada de publicaciones."""
    pub_names = list(publications.keys())
    if not pub_names:
        send_safe_message(
            bot, call.message.chat.id,
            "No hay publicaciones creadas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear publicación", callback_data="publicacion")]])
        )
        return

    page_size = 10
    total = len(pub_names)
    start = page
    end = min(start + page_size, total)
    page_pubs = pub_names[start:end]

    markup = InlineKeyboardMarkup(row_width=3)
    for name in page_pubs:
        pub = publications[name]
        markup.add(InlineKeyboardButton(f"#{pub.ID}", callback_data=f"ver_publicaciones_index:{name}"))

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"ver_publicaciones_search:{start-page_size}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"ver_publicaciones_search:{end}"))
    if nav:
        markup.row(*nav)
    markup.add(InlineKeyboardButton("Volver", callback_data="volver_menu"))

    send_safe_message(
        bot, call.message.chat.id,
        f"📋 Publicaciones ({start+1}-{end} de {total})\nPresiona el ID para ver detalles.",
        reply_markup=markup
    )

def show_publication_detail(bot, config, db, publications, scheduler, persistence, call, pub_name):
    """Muestra el detalle de una publicación y opciones de gestión."""
    pub = publications[pub_name]
    text = f"<b>ID:</b> {pub.ID}\n"
    text += f"<b>Nombre:</b> {pub.nombre}\n"
    text += f"<b>Canales:</b> {len(pub.canales)}\n"
    if pub.tiempo_publicacion:
        mins = pub.tiempo_publicacion // 60
        text += f"<b>Intervalo:</b> {mins} minutos\n"
    if pub.proxima_publicacion:
        rest = max(0, pub.proxima_publicacion - time.time())
        mins = int(rest // 60)
        text += f"<b>Próxima publicación:</b> en ~{mins} min\n"
    if pub.tiempo_eliminacion:
        mins = pub.tiempo_eliminacion // 60
        text += f"<b>Eliminación automática:</b> {mins} min después\n"
    text += f"<b>Multimedia:</b> {'Sí' if pub.multimedia else 'No'}\n"
    text += f"<b>Botones:</b> {'Sí' if pub.markup else 'No'}"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📨 Enviar ahora", callback_data=f"ver_publicaciones/send:{pub_name}"),
        InlineKeyboardButton("🗑 Eliminar publicación", callback_data=f"ver_publicaciones/del:{pub_name}"),
        InlineKeyboardButton("⏰ Programar hora exacta", callback_data=f"ver_publicaciones/time_to_post:{pub_name}"),
        InlineKeyboardButton("🔄 Cambiar intervalo", callback_data=f"ver_publicaciones/change_time:{pub_name}"),
        InlineKeyboardButton("👥 Gestionar canales", callback_data=f"ver_publicaciones/cc/:{pub_name}"),
        InlineKeyboardButton("🔙 Volver", callback_data="ver_publicaciones")
    )
    send_safe_message(bot, call.message.chat.id, text, reply_markup=markup)

def ask_for_time(bot, call, pub_name):
    """Pide al usuario una fecha/hora específica para la próxima publicación."""
    msg = bot.send_message(
        call.message.chat.id,
        "Envía la hora en formato:\n<code>Hora:Minuto:Día:Mes:Año</code>\n"
        "Ejemplo: <code>17:35:2:7:2030</code> (hora 24h, mes numérico, año 4 dígitos)\n"
        "O envía 'Cancelar' para abortar.",
        reply_markup=ReplyKeyboardMarkup(row_width=1).add("Cancelar")
    )
    bot.register_next_step_handler(msg, process_time_input, bot, config, db, publications, persistence, call, pub_name)

def process_time_input(message, bot, config, db, publications, persistence, call, pub_name):
    if message.text and message.text.lower() == "cancelar":
        bot.send_message(message.chat.id, "Operación cancelada.", reply_markup=ReplyKeyboardRemove())
        return
    try:
        parts = message.text.split(":")
        if len(parts) != 5:
            raise ValueError("Formato incorrecto")
        hora, minuto, dia, mes, anio = map(int, parts)
        # Construir struct_time
        t = time.struct_time((anio, mes, dia, hora, minuto, 0, 0, 0, -1))
        ts = time.mktime(t)
        # Ajustar a zona horaria de Perú (usando función de utils)
        from src.utils import calcular_diferencia_horaria
        ts_peru = calcular_diferencia_horaria(ts, "hora_peru")
        if ts_peru <= time.time():
            bot.send_message(message.chat.id, "La fecha debe ser futura. Intenta de nuevo.")
            ask_for_time(bot, call, pub_name)
            return
        publications[pub_name].proxima_publicacion = ts_peru
        persistence.save(publications)
        bot.send_message(message.chat.id, f"Próxima publicación programada para {time.strftime('%d/%m/%Y %H:%M', time.localtime(ts_peru))}", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}. Intenta de nuevo.", reply_markup=ReplyKeyboardRemove())
        ask_for_time(bot, call, pub_name)

def ask_for_new_interval(bot, call, pub_name):
    """Pide al usuario un nuevo intervalo en minutos."""
    msg = bot.send_message(
        call.message.chat.id,
        "Envía el nuevo intervalo en MINUTOS (ej: 120 para 2 horas).\n"
        "O 'Cancelar' para abortar.",
        reply_markup=ReplyKeyboardMarkup(row_width=1).add("Cancelar")
    )
    bot.register_next_step_handler(msg, process_interval_input, bot, config, db, publications, persistence, call, pub_name)

def process_interval_input(message, bot, config, db, publications, persistence, call, pub_name):
    if message.text and message.text.lower() == "cancelar":
        bot.send_message(message.chat.id, "Operación cancelada.", reply_markup=ReplyKeyboardRemove())
        return
    try:
        mins = int(message.text.strip())
        if mins < 0:
            raise ValueError("Debe ser positivo")
        publications[pub_name].tiempo_publicacion = mins * 60
        persistence.save(publications)
        bot.send_message(message.chat.id, f"Intervalo actualizado a {mins} minutos.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}. Intenta de nuevo.", reply_markup=ReplyKeyboardRemove())
        ask_for_new_interval(bot, call, pub_name)

# ---------- GESTIÓN DE CANALES DE UNA PUBLICACIÓN ----------
def handle_publication_channel_management(bot, config, db, publications, call):
    """Maneja añadir/eliminar canales de una publicación."""
    data = call.data
    user_id = call.from_user.id

    if data.startswith("ver_publicaciones/cc/:"):
        # Menú principal de gestión de canales para una publicación
        pub_name = data.split(":", 2)[2]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "Publicación no existe.")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Añadir canales", callback_data=f"ver_publicaciones/cc/anadir:{pub_name}"),
            InlineKeyboardButton("❌ Eliminar canales", callback_data=f"ver_publicaciones/cc/eliminar:{pub_name}"),
            InlineKeyboardButton("🔙 Volver", callback_data=f"ver_publicaciones_index:{pub_name}")
        )
        send_safe_message(bot, call.message.chat.id, "¿Qué deseas hacer con los canales de esta publicación?", reply_markup=markup)
        return

    if data.startswith("ver_publicaciones/cc/anadir:"):
        pub_name = data.split(":", 2)[2]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "Publicación no existe.")
            return
        # Mostrar canales disponibles para añadir
        temp_data[user_id] = {"pub_name": pub_name, "selected": [], "step": "add"}
        show_channels_for_publication_action(bot, db, call, 0, user_id, action="add")
        return

    if data.startswith("ver_publicaciones/cc/eliminar:"):
        pub_name = data.split(":", 2)[2]
        if pub_name not in publications:
            bot.answer_callback_query(call.id, "Publicación no existe.")
            return
        pub = publications[pub_name]
        if not pub.canales:
            send_safe_message(bot, call.message.chat.id, "Esta publicación no tiene canales para eliminar.")
            return
        temp_data[user_id] = {"pub_name": pub_name, "selected": [], "step": "remove"}
        show_channels_for_publication_action(bot, db, call, 0, user_id, action="remove", pub=pub)
        return

    # Callbacks de toggle, paginación, confirmación para añadir/eliminar
    if data.startswith("pub_chan_toggle:"):
        parts = data.split(":")
        action = parts[1]  # 'add' o 'remove'
        cid = int(parts[2])
        page = int(parts[3])
        user_id = call.from_user.id
        if user_id not in temp_data:
            return
        selected = temp_data[user_id].get("selected", [])
        if cid in selected:
            selected.remove(cid)
        else:
            selected.append(cid)
        temp_data[user_id]["selected"] = selected
        if action == "add":
            show_channels_for_publication_action(bot, db, call, page, user_id, action="add")
        else:
            pub_name = temp_data[user_id].get("pub_name")
            pub = publications.get(pub_name)
            if pub:
                show_channels_for_publication_action(bot, db, call, page, user_id, action="remove", pub=pub)
        return

    if data.startswith("pub_chan_page:"):
        parts = data.split(":")
        action = parts[1]
        page = int(parts[2])
        user_id = call.from_user.id
        if action == "add":
            show_channels_for_publication_action(bot, db, call, page, user_id, action="add")
        else:
            pub_name = temp_data.get(user_id, {}).get("pub_name")
            pub = publications.get(pub_name) if pub_name else None
            if pub:
                show_channels_for_publication_action(bot, db, call, page, user_id, action="remove", pub=pub)
        return

    if data.startswith("pub_chan_confirm:"):
        action = data.split(":")[1]
        user_id = call.from_user.id
        if user_id not in temp_data:
            return
        selected = temp_data[user_id].get("selected", [])
        pub_name = temp_data[user_id].get("pub_name")
        if not pub_name or pub_name not in publications:
            bot.answer_callback_query(call.id, "Publicación no existe.")
            return
        pub = publications[pub_name]
        if action == "add":
            for cid in selected:
                if cid not in pub.canales:
                    pub.canales.append(cid)
            bot.answer_callback_query(call.id, f"Se añadieron {len(selected)} canales.")
        else:  # remove
            for cid in selected:
                if cid in pub.canales:
                    pub.canales.remove(cid)
            bot.answer_callback_query(call.id, f"Se eliminaron {len(selected)} canales.")
        persistence.save(publications)
        temp_data[user_id] = {}
        # Volver al detalle de la publicación
        show_publication_detail(bot, config, db, publications, scheduler, persistence, call, pub_name)
        return

def show_channels_for_publication_action(bot, db, call, page, user_id, action="add", pub=None):
    """Muestra lista de canales para añadir o eliminar de una publicación."""
    if action == "add":
        channels = db.get_channels()
        selected = temp_data.get(user_id, {}).get("selected", [])
        pub_name = temp_data.get(user_id, {}).get("pub_name")
        if pub_name and pub_name in publications:
            existing = publications[pub_name].canales
            # Filtrar los que ya están
            channels = [ch for ch in channels if ch[0] not in existing]
    else:  # remove
        if not pub:
            return
        channels = [(cid, cid) for cid in pub.canales]  # Solo los canales de la publicación
        # Necesitamos nombres, así que consultamos db
        all_channels = db.get_channels()
        name_map = {cid: name for cid, name in all_channels}
        channels = [(cid, name_map.get(cid, str(cid))) for cid in pub.canales]

    if not channels:
        send_safe_message(
            bot, call.message.chat.id,
            "No hay canales disponibles para esta acción." if action == "add" else "No hay canales para eliminar."
        )
        return

    page_size = 6
    start = page
    end = min(start + page_size, len(channels))
    page_channels = channels[start:end]

    selected = temp_data.get(user_id, {}).get("selected", [])
    markup = InlineKeyboardMarkup(row_width=1)
    for cid, name in page_channels:
        is_sel = cid in selected
        markup.add(InlineKeyboardButton(f"✅ {name}" if is_sel else name, callback_data=f"pub_chan_toggle:{action}:{cid}:{page}"))

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"pub_chan_page:{action}:{start-page_size}"))
    if end < len(channels):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"pub_chan_page:{action}:{end}"))
    if nav:
        markup.row(*nav)
    markup.add(InlineKeyboardButton("✅ Confirmar", callback_data=f"pub_chan_confirm:{action}"))
    markup.add(InlineKeyboardButton("Cancelar", callback_data=f"ver_publicaciones_index:{temp_data.get(user_id, {}).get('pub_name', '')}"))

    send_safe_message(
        bot, call.message.chat.id,
        f"Selecciona canales para {'añadir' if action == 'add' else 'eliminar'}:",
        reply_markup=markup
    )