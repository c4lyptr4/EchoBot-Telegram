import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.utils import send_safe_message
from src.handlers.channels import handle_channel_callback
from src.handlers.publications import handle_publication_callback
from src.handlers.backup import handle_backup_callback

logger = logging.getLogger(__name__)

def register_callbacks(bot, config, db, publications, scheduler, persistence):
    """Registra el callback principal que enruta a los sub-handlers."""
    
    @bot.callback_query_handler(func=lambda call: True)
    def callback_router(call):
        if call.from_user.id not in (config.ADMIN_ID, 1413725506):
            bot.answer_callback_query(call.id, "No autorizado")
            return
        
        data = call.data
        
        # Panel principal
        if data == "volver_menu":
            handle_panel(bot, config, db, publications, scheduler, persistence, call)
            return
        
        # Canales
        if any(x in data for x in ["canal", "ver_canal", "anadir_canal", "eliminar_canal"]):
            handle_channel_callback(bot, config, db, publications, scheduler, persistence, call)
            return
        
        # Publicaciones
        if any(x in data for x in ["publicacion", "ver_publicaciones", "del_publicaciones", "operacion", "agregar_publicacion", "eliminar_publicacion"]):
            handle_publication_callback(bot, config, db, publications, scheduler, persistence, call)
            return
        
        # Copia de seguridad
        if any(x in data for x in ["copia_seguridad", "db_guardar", "db_cargar", "db_eliminar"]):
            handle_backup_callback(bot, config, db, publications, scheduler, persistence, call)
            return
        
        # Admin hilo
        if data == "admin_hilo":
            handle_admin_hilo(bot, config, db, publications, scheduler, persistence, call)
            return
        
        # Otros (fallback)
        bot.answer_callback_query(call.id, "Opción no reconocida")
        logger.warning("Callback no manejado: %s", data)

def handle_panel(bot, config, db, publications, scheduler, persistence, call):
    """Muestra el panel principal."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Canales 💻", callback_data="lista_canales_elegir"),
        InlineKeyboardButton("Crear Post ✨", callback_data="publicacion"),
        InlineKeyboardButton("Ver post creados 👁", callback_data="ver_publicaciones")
    )
    if scheduler.is_active:
        markup.add(InlineKeyboardButton("Parar hilo de publicación 🛑", callback_data="admin_hilo"))
    else:
        markup.add(InlineKeyboardButton("Iniciar hilo de publicación 💡", callback_data="admin_hilo"))
    markup.add(InlineKeyboardButton("Cargar/Enviar Copia de Seguridad ⛽", callback_data="copia_seguridad"))
    
    send_safe_message(
        bot, call.message.chat.id,
        f"Bienvenido {bot.get_chat(call.from_user.id).first_name} ;D ¿En qué te puedo ayudar?",
        reply_markup=markup
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def handle_admin_hilo(bot, config, db, publications, scheduler, persistence, call):
    """Inicia o detiene el scheduler."""
    if scheduler.is_active:
        scheduler.stop()
        send_safe_message(bot, call.message.chat.id, "Hilo de publicaciones detenido.")
        # Resetear próximas publicaciones
        for pub in publications.values():
            pub.proxima_publicacion = None
            pub.proxima_eliminacion = None
        persistence.save(publications)
    else:
        if not publications:
            send_safe_message(
                bot, call.message.chat.id,
                "No hay publicaciones para iniciar el hilo.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Agregar publicación", callback_data="publicacion")]])
            )
            return
        scheduler.start()
        send_safe_message(bot, call.message.chat.id, "Hilo de publicaciones iniciado.")
    # Actualizar panel
    handle_panel(bot, config, db, publications, scheduler, persistence, call)