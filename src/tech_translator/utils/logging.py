import logging

from tech_translator.config import Settings


def configure_logging(settings: Settings):
    logger = logging.getLogger("tech_translator")
    logger.setLevel(settings.logging.level)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
