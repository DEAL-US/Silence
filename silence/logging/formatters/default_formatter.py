import logging
import traceback

import colorama
from colorama import Fore, Style

colorama.init()

class DefaultFormatter(logging.Formatter):

    format_nolvl = "%(message)s"
    format_lvl = "[%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: Style.BRIGHT + Fore.BLACK + format_lvl + Style.RESET_ALL,
        logging.INFO: format_nolvl,
        logging.WARNING: Style.BRIGHT + Fore.YELLOW + format_lvl + Style.RESET_ALL,
        logging.ERROR: Style.BRIGHT + Fore.RED + format_lvl + Style.RESET_ALL,
        logging.CRITICAL: Style.BRIGHT + Fore.RED + format_lvl + Style.RESET_ALL
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

    
