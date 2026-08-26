import sqlite3
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class Database:
    """Maneja la base de datos SQLite de canales."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def init_db(self):
        """Crea la tabla si no existe."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS CANALES (
                ID INTEGER PRIMARY KEY,
                NOMBRE VARCHAR
            )
        """)
        self.conn.commit()
        logger.info("Base de datos SQLite inicializada en %s", self.db_path)
    
    def get_channels(self) -> List[Tuple[int, str]]:
        """Retorna todos los canales como lista de (id, nombre)."""
        self.cursor.execute("SELECT ID, NOMBRE FROM CANALES")
        return self.cursor.fetchall()
    
    def get_channel_ids(self) -> List[int]:
        """Retorna solo los IDs."""
        self.cursor.execute("SELECT ID FROM CANALES")
        return [row[0] for row in self.cursor.fetchall()]
    
    def add_channel(self, chat_id: int, name: str) -> bool:
        """Añade un canal. Retorna True si éxito."""
        try:
            self.cursor.execute("INSERT INTO CANALES (ID, NOMBRE) VALUES (?, ?)", (chat_id, name))
            self.conn.commit()
            logger.info("Canal agregado: %d (%s)", chat_id, name)
            return True
        except sqlite3.IntegrityError:
            logger.warning("Canal ya existe: %d", chat_id)
            return False
        except Exception as e:
            logger.error("Error agregando canal: %s", e)
            return False
    
    def remove_channel(self, chat_id: int) -> bool:
        """Elimina un canal por ID."""
        try:
            self.cursor.execute("DELETE FROM CANALES WHERE ID = ?", (chat_id,))
            self.conn.commit()
            logger.info("Canal eliminado: %d", chat_id)
            return True
        except Exception as e:
            logger.error("Error eliminando canal: %s", e)
            return False
    
    def channel_exists(self, chat_id: int) -> bool:
        """Verifica si un canal está registrado."""
        self.cursor.execute("SELECT 1 FROM CANALES WHERE ID = ?", (chat_id,))
        return self.cursor.fetchone() is not None
    
    def close(self):
        if self.conn:
            self.conn.close()