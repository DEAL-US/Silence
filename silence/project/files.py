import hashlib
import json
import os
import tempfile

###############################################################################
# The files of the project (silence.json, endpoints/*.json, tests/*.json, the
# log of requests): reading, writing them at once, and their version (etag), so
# that two clients (the admin panel and an editor) do not overwrite each other's
# changes.
###############################################################################

def etag_of(path):
    '''Version of a file: a hash of its content ("" if it does not exist)'''
    return read_with_etag(path)[1]


def read_with_etag(path):
    '''The text of a file and its version, read at once (so that they match): (None, "") if it
    does not exist'''
    if not os.path.isfile(path):
        return None, ""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf8", errors="replace"), hashlib.sha1(raw).hexdigest()[:16]


def read_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf8") as f:
        return json.load(f)


def write_text(path, text):
    """Writes a file at once: in a temporary file next to it, which then replaces it, so that
    whoever reads it (the watcher, the registry of endpoints, an editor) never sees it half
    written. Returns its new etag"""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return etag_of(path)


def write_json(path, data):
    """Writes a JSON file of the project (indented, UTF-8) at once. Returns its new etag"""
    return write_text(path, json.dumps(data, indent=4, ensure_ascii=False, default=str) + "\n")


def safe_name(name):
    '''A file or entry name without paths: letters, digits, _ and -'''
    name = (name or "").removesuffix(".json")
    if not name or not all(c.isalnum() or c in "_-" for c in name):
        raise ValueError(f"Invalid name '{name}'")
    return name
