from silence.settings import settings

from colorama import Fore, Style

import logging
import re

###############################################################################
# Filters and modifies Flask's log records in-place
###############################################################################

# Regex to remove ANSI color codes from log lines
RE_ANSI = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
RE_LOG = re.compile(r'(.*) - - \[(.*)\] "(\w+) (/.*) HTTP.*" (.*) -.*')

COLORS = {
    "GREEN": Style.BRIGHT + Fore.GREEN if settings.COLORED_OUTPUT else "",
    "MAGENTA": Style.BRIGHT + Fore.MAGENTA if settings.COLORED_OUTPUT else "",
    "CYAN": Style.BRIGHT + Fore.CYAN if settings.COLORED_OUTPUT else "",
    "YELLOW": Style.BRIGHT + Fore.YELLOW if settings.COLORED_OUTPUT else "",
    "RED": Style.BRIGHT + Fore.RED if settings.COLORED_OUTPUT else "",
    "WHITE": Style.BRIGHT + Fore.WHITE if settings.COLORED_OUTPUT else "",
}
RESET = Style.RESET_ALL if settings.COLORED_OUTPUT else ""

class FlaskFilter(logging.Filter):

    def filter(self, record):
        msg = record.msg

        if msg.startswith(" * Running on"):
            record.msg = msg[3:]
            return True

        # Construct the full message by adding the
        # variable arguments to the message
        msg = RE_ANSI.sub('', msg)
        args = tuple(RE_ANSI.sub('', x) for x in record.args)

        msg = msg % args

        m = RE_LOG.match(msg)
        if m:
            addr, date, verb, route, code = m.groups()
            
            if route.startswith(settings.API_PREFIX):
                api_web = "[API]"
                api_color = COLORS["MAGENTA"]
            else:
                api_web = "[WEB]"
                api_color = COLORS["CYAN"]

            if code[0] in ('2', '3'):
                code_color = COLORS["GREEN"]
            elif code[0] == '4':
                code_color = COLORS["YELLOW"]
            elif code[0] == '5':
                code_color = COLORS["RED"]
            else:
                code_color = COLORS["WHITE"]

            record.msg = f"{date} | {api_color}{api_web}{RESET} " + \
                  f"{verb} {route} from {addr} - {code_color}{code}{RESET}"
            record.args = ()
        else:
            print("MSG:", msg)
            print("ARGS:", record.args)
        return True