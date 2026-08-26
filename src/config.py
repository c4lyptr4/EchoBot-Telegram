import os
from pathlib import Path

class Config:
    """Configuración centralizada desde variables de entorno."""
    
    # Variables obligatorias
    TOKEN = os.environ.get("TOKEN")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
    
    # Opcionales
    HOST_URL = os.environ.get("HOST_URL")          # MongoDB para backups
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")    # Si se usa webhook
    PORT = int(os.environ.get("PORT", 5000))
    P_VERSION = os.environ.get("P_VERSION")
    
    # Rutas
    BASE_DIR = Path(__file__).parent.parent
    PUBLICATIONS_FILE = BASE_DIR / "publicaciones.dill"
    DB_PATH = BASE_DIR / "BD_Canales.db"
    MEDIA_DIR = BASE_DIR / "Publicaciones_media"
    
    @classmethod
    def validate(cls):
        """Verifica que las variables obligatorias estén presentes."""
        if not cls.TOKEN:
            return False
        if not cls.ADMIN_ID:
            return False
        return True