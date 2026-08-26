import logging
import telebot
from telebot import apihelper
from telebot.types import BotCommand
from src.config import Config
from src.database import Database
from src.scheduler import Scheduler
from src.persistence import Persistence
from src.handlers.commands import register_commands
from src.handlers.callbacks import register_callbacks
import requests.adapters

logger = logging.getLogger(__name__)

def create_bot(config: Config, db: Database, publications: dict, scheduler: Scheduler, persistence: Persistence):
    # Habilitar middleware
    apihelper.ENABLE_MIDDLEWARE = True
    
    # Configurar timeouts más largos para todas las peticiones a la API
    apihelper.CONNECT_TIMEOUT = 60   # 60 segundos para conexión
    apihelper.READ_TIMEOUT = 60      # 60 segundos para lectura
    
    # Crear sesión de requests con adaptador que soporte reintentos
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    apihelper._get_req_session = lambda: session  # Sobrescribir la sesión por defecto
    
    bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML", disable_web_page_preview=True)
    
    # Configurar comandos (con manejo de errores de red)
    try:
        bot.set_my_commands([
            BotCommand("/help", "Ayuda con el bot"),
            BotCommand("/host", "Información sobre el host"),
            BotCommand("/panel", "Acceso al panel de control"),
        ], scope=telebot.types.BotCommandScopeChat(config.ADMIN_ID))
        logger.info("Comandos registrados correctamente")
    except Exception as e:
        logger.warning(f"No se pudieron registrar los comandos (error de red): {e}")
        # El bot seguirá funcionando sin comandos, solo se muestran en el menú de Telegram.
    
    # Middleware para limpiar archivos temporales
    @bot.middleware_handler()
    def middleware(bot_instance, update):
        if update.callback_query and "db" not in update.callback_query.data:
            import os
            if "Copia_Seguridad.zip" in os.listdir():
                os.remove("Copia_Seguridad.zip")
    
    # Registrar handlers
    register_commands(bot, config, db, publications, scheduler, persistence)
    register_callbacks(bot, config, db, publications, scheduler, persistence)
    
    logger.info("Bot creado y handlers registrados")
    return bot