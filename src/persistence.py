import os
import logging
import dill
from typing import Dict
from src.models import Publicacion

logger = logging.getLogger(__name__)

class Persistence:
    """Maneja la carga/guardado del diccionario de publicaciones con dill."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def load(self) -> Dict[str, Publicacion]:
        """Carga el diccionario desde el archivo. Si no existe, retorna vacío."""
        if not os.path.isfile(self.filepath):
            logger.info("Archivo de publicaciones no encontrado. Se creará uno nuevo.")
            return {}
        try:
            with open(self.filepath, "rb") as f:
                data = dill.load(f)
            logger.info("Publicaciones cargadas: %d", len(data))
            return data
        except Exception as e:
            logger.error("Error cargando publicaciones: %s", e)
            return {}
    
    def save(self, publications: Dict[str, Publicacion]) -> bool:
        """Guarda el diccionario en el archivo."""
        try:
            with open(self.filepath, "wb") as f:
                dill.dump(publications, f)
            logger.info("Publicaciones guardadas: %d", len(publications))
            return True
        except Exception as e:
            logger.error("Error guardando publicaciones: %s", e)
            return False