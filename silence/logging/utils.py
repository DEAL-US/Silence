from colorama import Fore, Style

from silence.settings import settings

###############################################################################
# The colors of the lines that Silence writes in its console.
###############################################################################

COLORS = {
    "GREEN": Style.BRIGHT + Fore.GREEN if settings.COLORED_OUTPUT else "",
    "MAGENTA": Style.BRIGHT + Fore.MAGENTA if settings.COLORED_OUTPUT else "",
    "CYAN": Style.BRIGHT + Fore.CYAN if settings.COLORED_OUTPUT else "",
    "YELLOW": Style.BRIGHT + Fore.YELLOW if settings.COLORED_OUTPUT else "",
    "RED": Style.BRIGHT + Fore.RED if settings.COLORED_OUTPUT else "",
}
RESET = Style.RESET_ALL if settings.COLORED_OUTPUT else ""
