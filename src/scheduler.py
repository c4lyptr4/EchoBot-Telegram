import threading
import time
import logging
from typing import Dict, Optional
from src.models import Publicacion
from src.database import Database
from src.publisher import Publisher

logger = logging.getLogger(__name__)

class Scheduler:
    """
    Controla el hilo que revisa y ejecuta las publicaciones periódicas.
    """
    def __init__(self, publications: Dict[str, Publicacion], db: Database, admin_id: int):
        self.publications = publications
        self.db = db
        self.admin_id = admin_id
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.publisher = Publisher()
    
    def start(self):
        """Inicia el hilo del scheduler."""
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Scheduler iniciado")
    
    def stop(self):
        """Detiene el hilo del scheduler."""
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Scheduler detenido")
    
    def _run(self):
        """Bucle principal del scheduler."""
        while not self.stop_event.is_set():
            try:
                now = time.time()
                # Recorremos una copia para evitar errores si se modifica durante la iteración
                for nombre, pub in list(self.publications.items()):
                    # Comprobar eliminación
                    if pub.proxima_eliminacion and now >= pub.proxima_eliminacion:
                        self.publisher.delete_publication(pub, self.db)
                        pub.proxima_eliminacion = None
                        pub.lista_message_id_eliminar = None
                    
                    # Comprobar publicación
                    if pub.proxima_publicacion and now >= pub.proxima_publicacion:
                        self.publisher.send_publication(pub, self.db)
                        # Calcular siguiente
                        pub.proxima_publicacion = now + pub.tiempo_publicacion
                        if pub.tiempo_eliminacion:
                            pub.proxima_eliminacion = now + pub.tiempo_eliminacion
                
                # Esperar 30 segundos o hasta que se reciba señal de parada
                self.stop_event.wait(30)
            except Exception as e:
                logger.exception("Error en bucle del scheduler: %s", e)
                time.sleep(30)
        logger.info("Bucle del scheduler terminado")
    
    @property
    def is_active(self) -> bool:
        return self.running