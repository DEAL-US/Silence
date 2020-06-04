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

class FlaskFilter(logging.Filter):

    def filter(self, record):
        msg = record.msg

        if msg.startswith(" * Running on"):
            record.msg = msg[3:]
            return True

        msg = RE_ANSI.sub('', msg)
        m = RE_LOG.match(msg)
        if m:
            addr, date, verb, route, code = m.groups()
            
            if route.startswith(settings.API_PREFIX):
                api_web = "[API]"
                api_color = Fore.MAGENTA
            else:
                api_web = "[WEB]"
                api_color = Fore.CYAN

            if code[0] in ('2', '3'):
                code_color = Fore.GREEN
            elif code[0] == '4':
                code_color = Fore.YELLOW
            elif code[0] == '5':
                code_color = Fore.RED
            else:
                code_color = Fore.WHITE

            record.msg = f"{date} | {api_color}{Style.BRIGHT}{api_web}{Style.RESET_ALL} " +\
                  f"{verb} {route} from {addr} - {code_color}{Style.BRIGHT}{code}{Style.RESET_ALL}"
        return True