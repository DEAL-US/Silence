import os
import threading
import time

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger

###############################################################################
# Watches the files of the project (silence.json, endpoints/*.json and
# tests/*.json) and reloads them when they change, whoever changes them (the
# admin panel, an editor, git...).
###############################################################################

_snapshot = {}


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
        if settings.errors:
            logger.error("%s has errors (the previous values are kept until they are fixed):", PROJECT_FILE)
            for err in settings.errors:
                logger.error("    · %s", err)
        schema.invalidate()
    if any(os.path.basename(os.path.dirname(p)) == "endpoints" for p in changed) or \
            any(os.path.basename(p) == PROJECT_FILE for p in changed):
        REGISTRY.load().log_errors()
        from silence.testing.generator import write_generated_tests
        write_generated_tests()  # The tests follow the endpoints
    if settings.errors and rel == [PROJECT_FILE]:
        return  # Already reported: nothing has been reloaded
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
