#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

print("TOKEN cargado:", os.getenv("TOKEN"))
print("ADMIN_ID cargado:", os.getenv("ADMIN_ID"))

from src.config import Config
from src.database import Database
from src.persistence import Persistence
from src.scheduler import Scheduler
from src.bot import create_bot
from src.utils import setup_logging

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    config = Config()
    if not config.validate():
        logger.error("Configuración inválida. Revisa las variables de entorno.")
        sys.exit(1)

    db = Database(config.DB_PATH)
    db.init_db()

    persistence = Persistence(config.PUBLICATIONS_FILE)
    publications = persistence.load()

    scheduler = Scheduler(publications, db, config.ADMIN_ID)
    scheduler.start()

    bot_app = create_bot(config, db, publications, scheduler, persistence)

    if config.WEBHOOK_URL:
        logger.info("Arrancando con webhook en %s", config.WEBHOOK_URL)
        bot_app.run_webhook(config.WEBHOOK_URL, port=config.PORT)
    else:
        logger.info("Arrancando con polling (timeout=60, reintentos automáticos)")
        # Polling robusto con timeout extendido y non_stop=True para que no se caiga por errores de red
        bot_app.polling(timeout=60, non_stop=True, interval=2)

if __name__ == "__main__":
    main()