import os
import threading
from datetime import datetime
from urllib.parse import quote

from silence.settings import settings

###############################################################################
# The log of the requests to the student's app (admin/logs/requests.log), as
# the access log of any web server: one line per request, and nothing else.
# The admin panel shows it in its console and sums it up in its statistics;
# deleting the file resets both. The panel's own requests (/admin and the
# admin API) are not logged.
#
#   2026-11-08T08:01:12 api GET /api/employees/3 200 4ms 312B /employees/$employeeId
#   2026-11-08T08:01:13 web GET /css/main.css 404 1ms 0B - Not found
#
# Fields: time, group (api: the student's endpoints; silence: login, register
# and GET <prefix>; web: the files of web/), method, path (with the query
# string), status, time taken, bytes sent, the route of the endpoint that
# answered ("-" if none) and, in errors, the message.
###############################################################################

MAX_LINES = 10000  # The older ones are removed (when there are 10% more)

_lock = threading.Lock()
_lines = None  # Lines in the file (None: not counted yet)


def log_path():
    return os.path.join(settings.PROJECT_DIR, "admin", "logs", "requests.log")


def line(group, method, path, query, status, ms, size, route=None, message=None):
    text = (f"{datetime.now().isoformat(timespec='seconds')} {group} {method} "
            f"{quote(path, safe='/$-_.~@:+,;=!*()')}{'?' + query if query else ''} "
            f"{status} {round(ms)}ms {size}B {route or '-'}")
    if message:
        text += " " + " ".join(str(message).split())
    return text


def write(text):
    '''Appends a line (the file is created again if it was deleted)'''
    global _lines
    path = log_path()
    with _lock:
        try:
            if not os.path.isfile(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                _lines = 0
            elif _lines is None:
                with open(path, encoding="utf8", errors="replace") as f:
                    _lines = sum(1 for _ in f)
            with open(path, "a", encoding="utf8") as f:
                f.write(text + "\n")
            _lines += 1
            if _lines > MAX_LINES * 1.1:
                with open(path, encoding="utf8", errors="replace") as f:
                    kept = f.readlines()[-MAX_LINES:]
                with open(path, "w", encoding="utf8") as f:
                    f.writelines(kept)
                _lines = len(kept)
        except OSError:
            _lines = None  # E.g., a read-only folder: the app works without its log
