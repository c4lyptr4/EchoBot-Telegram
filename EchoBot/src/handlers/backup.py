import logging
import os
import time
import re
import pymongo
from zipfile import ZipFile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.utils import send_safe_message, calcular_diferencia_horaria

logger = logging.getLogger(__name__)

def handle_backup_callback(bot, config, db, publications, scheduler, persistence, call):
    """Maneja callbacks de copias de seguridad."""
    data = call.data
    
    if data == "copia_seguridad":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Guardar Copia 💾", callback_data="db_guardar"),
            InlineKeyboardButton("Cargar Copias 💫", callback_data="db_cargar")
        )
        send_safe_message(
            bot, call.message.chat.id,
            "Aquí puedes guardar o cargar copias de seguridad.\n"
            "Las copias se almacenan en MongoDB.",
            reply_markup=markup
        )
        return
    
    if data == "db_guardar":
        perform_backup(bot, config, call)
        return
    
    if data == "db_cargar":
        list_backups(bot, config, call)
        return
    
    if data.startswith("db_cargar:"):
        restore_backup(bot, config, db, publications, persistence, call, data)
        return
    
    if data.startswith("db_eliminar:"):
        delete_backup(bot, config, call, data)
        return

def perform_backup(bot, config, call):
    """Guarda una copia de seguridad en MongoDB."""
    if not config.HOST_URL:
        send_safe_message(bot, call.message.chat.id, "HOST_URL no configurado. No se puede guardar copia.")
        return
    
    # Crear zip con BD y publicaciones
    zip_path = "Copia_Seguridad.zip"
    with ZipFile(zip_path, "w") as zf:
        if os.path.exists(config.DB_PATH):
            zf.write(config.DB_PATH)
        if os.path.exists(config.PUBLICATIONS_FILE):
            zf.write(config.PUBLICATIONS_FILE)
    
    # Conectar a MongoDB
    try:
        client = pymongo.MongoClient(config.HOST_URL)
        db = client["BaseDatos"]
        collection = db["CopiaSeguridad"]
        
        with open(zip_path, "rb") as f:
            data = f.read()
        doc = {
            "fecha": time.time(),
            "archivo": data
        }
        result = collection.insert_one(doc)
        doc_id = result.inserted_id
        fecha = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
        send_safe_message(
            bot, call.message.chat.id,
            f"Copia guardada con ID: {doc_id}\nFecha: {fecha}"
        )
    except Exception as e:
        logger.exception("Error guardando backup")
        send_safe_message(bot, call.message.chat.id, f"Error: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

def list_backups(bot, config, call):
    """Lista las copias de seguridad disponibles."""
    if not config.HOST_URL:
        send_safe_message(bot, call.message.chat.id, "HOST_URL no configurado.")
        return
    try:
        client = pymongo.MongoClient(config.HOST_URL)
        db = client["BaseDatos"]
        collection = db["CopiaSeguridad"]
        backups = collection.find().sort("fecha", -1)
        count = 0
        for doc in backups:
            count += 1
            doc_id = doc["_id"]
            fecha = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(doc["fecha"]))
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("Cargar", callback_data=f"db_cargar:{doc_id}"),
                InlineKeyboardButton("Eliminar", callback_data=f"db_eliminar:{doc_id}")
            )
            bot.send_message(
                call.message.chat.id,
                f"ID: {doc_id}\nFecha: {fecha}",
                reply_markup=markup
            )
        if count == 0:
            send_safe_message(bot, call.message.chat.id, "No hay copias de seguridad.")
    except Exception as e:
        logger.exception("Error listando backups")
        send_safe_message(bot, call.message.chat.id, f"Error: {e}")

def restore_backup(bot, config, db, publications, persistence, call, data):
    """Restaura una copia de seguridad desde MongoDB."""
    if scheduler.is_active:
        send_safe_message(bot, call.message.chat.id, "Detén el hilo de publicaciones antes de restaurar.")
        return
    doc_id = data.split(":")[1]
    try:
        client = pymongo.MongoClient(config.HOST_URL)
        db = client["BaseDatos"]
        collection = db["CopiaSeguridad"]
        doc = collection.find_one({"_id": doc_id})
        if not doc:
            send_safe_message(bot, call.message.chat.id, "Copia no encontrada.")
            return
        # Extraer zip
        zip_path = "Copia_Seguridad.zip"
        with open(zip_path, "wb") as f:
            f.write(doc["archivo"])
        # Descomprimir y reemplazar archivos
        with ZipFile(zip_path, "r") as zf:
            zf.extractall(config.BASE_DIR)
        # Recargar publicaciones
        new_publications = persistence.load()
        publications.clear()
        publications.update(new_publications)
        # Reabrir DB
        db.init_db()
        send_safe_message(bot, call.message.chat.id, "Copia restaurada correctamente.")
        os.remove(zip_path)
    except Exception as e:
        logger.exception("Error restaurando backup")
        send_safe_message(bot, call.message.chat.id, f"Error: {e}")

def delete_backup(bot, config, call, data):
    """Elimina una copia de seguridad."""
    doc_id = data.split(":")[1]
    try:
        client = pymongo.MongoClient(config.HOST_URL)
        db = client["BaseDatos"]
        collection = db["CopiaSeguridad"]
        collection.delete_one({"_id": doc_id})
        send_safe_message(bot, call.message.chat.id, "Copia eliminada.")
    except Exception as e:
        logger.exception("Error eliminando backup")
        send_safe_message(bot, call.message.chat.id, f"Error: {e}")