import logging
import sys
import logging
import sys
import codecs
import os
import traceback

# Настройка кодировки stdout и stderr
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "replace")
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "replace")

# Создание папки logs
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Гарантируем абсолютный путь
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

os.makedirs(LOG_DIR, exist_ok=True)  # Создаём папку, если её нет

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.__stdout__),
    ],
)

logger = logging.getLogger()

def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.error("Uncaught Exception:\n" + error_msg)

sys.excepthook = log_uncaught_exceptions

logger.info("Starting logger...")
