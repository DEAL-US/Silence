import logging
import colorama

from colorama import Fore, Style
from silence.settings import settings

if settings.COLORED_OUTPUT:
    colorama.init()

def add_color(color, format_str):
    if settings.COLORED_OUTPUT:
        return Style.BRIGHT + color + format_str + Style.RESET_ALL
    else:
        return format_str

class DefaultFormatter(logging.Formatter):

    format_nolvl = "%(message)s"
    format_lvl = "[%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: add_color(Fore.BLACK, format_lvl),
        logging.INFO: format_nolvl,
        logging.WARNING: add_color(Fore.YELLOW, format_lvl),
        logging.ERROR: add_color(Fore.RED, format_lvl),
        logging.CRITICAL: add_color(Fore.RED, format_lvl)
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        res = formatter.format(record)
        
        # If we're logging an exception, print the stack trace in red
        if record.exc_info:
            res = res.replace(Style.RESET_ALL, "")
            res += Style.RESET_ALL

        return res
