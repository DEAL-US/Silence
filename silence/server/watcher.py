import os
import threading
import time

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger

###############################################################################
# Watches the files of the project (silence.json, endpoints/*.json and
# tests/*.json) and reloads them when they change, whoever changes them (the
# admin panel, an editor, git...). Every reload increases the revision, which
# clients read in GET /_silence/v1/status to know that something changed.
###############################################################################

_lock = threading.Lock()
_revision = 0
_snapshot = {}


def revision():
    return _revision


def bump():
    global _revision
    with _lock:
        _revision += 1
    return _revision


def watched_files():
    files = [os.path.join(settings.PROJECT_DIR, PROJECT_FILE)]
    for folder in ("endpoints", "tests"):
        path = os.path.join(settings.PROJECT_DIR, folder)
        if os.path.isdir(path):
            files += [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]
    return files


def take_snapshot():
    res = {}
    for path in watched_files():
        try:
            st = os.stat(path)
            res[path] = (st.st_mtime_ns, st.st_size)
        except OSError:
            pass
    return res


def reload(changed):
    '''Reloads what depends on the changed files'''
    from silence.db import schema
    from silence.server.endpoints import REGISTRY

    rel = sorted(os.path.relpath(p, settings.PROJECT_DIR) for p in changed)
    if any(os.path.basename(p) == PROJECT_FILE for p in changed):
        settings.load(settings.PROJECT_DIR)
        schema.invalidate()
    if any(os.path.basename(os.path.dirname(p)) in ("endpoints",) for p in changed) or \
            any(os.path.basename(p) == PROJECT_FILE for p in changed):
        REGISTRY.load()
    bump()
    logger.info("Reloaded %s", ", ".join(rel))


def check():
    '''Compares the files with the last snapshot and reloads if something changed'''
    global _snapshot
    current = take_snapshot()
    changed = {p for p in set(current) | set(_snapshot) if current.get(p) != _snapshot.get(p)}
    _snapshot = current
    if changed:
        try:
            reload(changed)
        except Exception as exc:
            logger.error("Cannot reload %s: %s", ", ".join(sorted(changed)), exc)


def start(interval=1.0):
    global _snapshot
    _snapshot = take_snapshot()

    def loop():
        while True:
            time.sleep(interval)
            check()

    threading.Thread(target=loop, name="silence-watcher", daemon=True).start()
