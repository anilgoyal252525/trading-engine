import logging
import logging.handlers
import os
from datetime import datetime
from queue import Queue

# --- Setup log folder ---
LOG_DIR = os.path.join(os.getcwd(), "logger_files", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# --- Queue for async logging ---
log_queue = Queue(-1)  # Infinite size

# --- Log file with today's date ---
today_str = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"main_script_{today_str}.log")

# --- File handler (rotates daily) ---
file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=30, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))

# --- Console handler ---
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))

# --- Queue handler (pushes logs to queue) ---
queue_handler = logging.handlers.QueueHandler(log_queue)

# --- Root logger setup ---
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(queue_handler)  # push logs to queue

# --- Queue listener runs in background thread ---
listener = logging.handlers.QueueListener(log_queue, file_handler, console_handler)
listener.start()

# --- Your project logger ---
logger = logging.getLogger(__name__)
