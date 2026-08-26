import time
from typing import Optional, List, Dict, Any

class Publicacion:
    """
    Modelo de una publicación.
    Se mantiene casi idéntico al original para compatibilidad.
    """
    def __init__(
        self,
        ID: str,
        texto: str,
        canales: List[int],
        tiempo_publicacion: int,   # en segundos
        nombre: str,
        multimedia: Optional[List[str]] = None,   # [ruta, tipo]
        markup: Optional[Any] = None,
    ):
        self.ID = ID
        self.texto = texto
        self.canales = canales
        self.tiempo_publicacion = tiempo_publicacion
        self.nombre = nombre
        self.multimedia = multimedia
        self.markup = markup
        
        # Estos atributos se actualizan durante la ejecución
        self.proxima_publicacion: Optional[float] = None
        self.tiempo_eliminacion: Optional[int] = None   # en segundos
        self.proxima_eliminacion: Optional[float] = None
        self.lista_message_id_eliminar: Optional[List] = None

    def mostrar_publicacion(self):
        """
        Devuelve un diccionario con el contenido listo para enviar y
        una lista de cadenas informativas (tiempos restantes).
        """
        diccionario = {}
        if self.multimedia:
            tipo = self.multimedia[1]
            ruta = self.multimedia[0]
            if tipo == "photo":
                diccionario["photo"] = [ruta, self.texto, self.markup] if self.markup else [ruta, self.texto]
            elif tipo == "voice":
                diccionario["voice"] = [ruta, self.texto, self.markup] if self.markup else [ruta, self.texto]
            elif tipo == "video":
                diccionario["video"] = [ruta, self.texto, self.markup] if self.markup else [ruta, self.texto]
            elif tipo == "audio":
                diccionario["audio"] = [ruta, self.texto, self.markup] if self.markup else [ruta, self.texto]
            elif tipo == "document":
                diccionario["document"] = [ruta, self.texto, self.markup] if self.markup else [ruta, self.texto]
        else:
            diccionario["text"] = [self.texto, self.markup] if self.markup else [self.texto]
        
        lista_opcional = []
        if self.proxima_publicacion:
            restante = max(0, self.proxima_publicacion - time.time())
            minutos = int(restante // 60)
            horas = minutos // 60
            minutos = minutos % 60
            if horas > 0:
                lista_opcional.append(f"Para el próximo envío de la Publicación <b>{self.ID}</b> faltan {horas} hora(s) y {minutos} minuto(s)")
            else:
                lista_opcional.append(f"Para el próximo envío de la Publicación <b>{self.ID}</b> faltan {minutos} minuto(s)")
        if self.proxima_eliminacion:
            restante = max(0, self.proxima_eliminacion - time.time())
            minutos = int(restante // 60)
            horas = minutos // 60
            minutos = minutos % 60
            if horas > 0:
                lista_opcional.append(f"Para la próxima eliminación de la Publicación <b>{self.ID}</b> faltan {horas} hora(s) y {minutos} minuto(s)")
            else:
                lista_opcional.append(f"Para la próxima eliminación de la Publicación <b>{self.ID}</b> faltan {minutos} minuto(s)")
        
        return diccionario, lista_opcional