import logging
from .settings import LOG_FILE

def configurar_logs():
    """Configura o sistema de logging"""
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S'
    )
    logger = logging.getLogger('TorqView')
    logger.info("Aplicativo iniciado")
    return logger
