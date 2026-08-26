import logging
import time
from typing import Dict
from src.models import Publicacion
from src.database import Database
import telebot

logger = logging.getLogger(__name__)

class Publisher:
    """Encargado de enviar y eliminar publicaciones en los canales."""
    
    def send_publication(self, pub: Publicacion, db: Database, bot: telebot.TeleBot):
        """
        Envía la publicación a todos sus canales.
        Guarda los IDs de los mensajes para posible eliminación.
        """
        if not pub.canales:
            logger.warning("Publicación %s sin canales", pub.ID)
            return
        
        contenido, _ = pub.mostrar_publicacion()
        msg_ids = []
        
        for canal_id in pub.canales:
            try:
                # Enviar según el tipo de contenido
                for tipo, datos in contenido.items():
                    if tipo == "photo":
                        with open(datos[0], "rb") as f:
                            if len(datos) == 3:
                                msg = bot.send_photo(canal_id, f, caption=datos[1], reply_markup=datos[2])
                            else:
                                msg = bot.send_photo(canal_id, f, caption=datos[1])
                    elif tipo == "video":
                        with open(datos[0], "rb") as f:
                            if len(datos) == 3:
                                msg = bot.send_video(canal_id, f, caption=datos[1], reply_markup=datos[2])
                            else:
                                msg = bot.send_video(canal_id, f, caption=datos[1])
                    elif tipo == "audio":
                        with open(datos[0], "rb") as f:
                            if len(datos) == 3:
                                msg = bot.send_audio(canal_id, f, caption=datos[1], reply_markup=datos[2])
                            else:
                                msg = bot.send_audio(canal_id, f, caption=datos[1])
                    elif tipo == "document":
                        with open(datos[0], "rb") as f:
                            if len(datos) == 3:
                                msg = bot.send_document(canal_id, f, caption=datos[1], reply_markup=datos[2])
                            else:
                                msg = bot.send_document(canal_id, f, caption=datos[1])
                    elif tipo == "voice":
                        with open(datos[0], "rb") as f:
                            if len(datos) == 3:
                                msg = bot.send_voice(canal_id, f, caption=datos[1], reply_markup=datos[2])
                            else:
                                msg = bot.send_voice(canal_id, f, caption=datos[1])
                    else:  # text
                        if len(datos) == 2:
                            msg = bot.send_message(canal_id, datos[0], reply_markup=datos[1], parse_mode="HTML")
                        else:
                            msg = bot.send_message(canal_id, datos[0], parse_mode="HTML")
                    
                    msg_ids.append(msg.message_id)
                    break  # Solo enviamos un tipo por publicación
            except Exception as e:
                logger.error("Error enviando a canal %d: %s", canal_id, e)
                # Notificar al admin? (se hará en el handler)
        
        pub.lista_message_id_eliminar = msg_ids
        logger.info("Publicación %s enviada a %d canales", pub.ID, len(pub.canales))
    
    def delete_publication(self, pub: Publicacion, db: Database, bot: telebot.TeleBot):
        """Elimina los mensajes de la publicación en todos sus canales."""
        if not pub.lista_message_id_eliminar:
            return
        for idx, msg_id in enumerate(pub.lista_message_id_eliminar):
            if idx >= len(pub.canales):
                break
            canal_id = pub.canales[idx]
            try:
                bot.delete_message(canal_id, msg_id)
                logger.debug("Mensaje %d eliminado del canal %d", msg_id, canal_id)
            except Exception as e:
                logger.warning("No se pudo eliminar mensaje %d en canal %d: %s", msg_id, canal_id, e)
        pub.lista_message_id_eliminar = None
        pub.proxima_eliminacion = None