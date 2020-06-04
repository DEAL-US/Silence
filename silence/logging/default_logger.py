import logging

from silence.settings import settings
from silence.logging.default_formatter import DefaultFormatter


logger = logging.getLogger("silence")
log_lvl = logging.DEBUG if settings.DEBUG_ENABLED else logging.INFO
logger.setLevel(log_lvl)

ch = logging.StreamHandler()
ch.setLevel(log_lvl)
ch.setFormatter(DefaultFormatter())

logger.addHandler(ch)