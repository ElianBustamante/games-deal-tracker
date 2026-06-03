import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "bot-steam-epic.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logging():
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Already configured
        return
        
    root_logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Rotating File Handler (Max 5MB per file, keeping 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5 * 1024 * 1024, 
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
