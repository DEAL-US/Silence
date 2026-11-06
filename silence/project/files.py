import hashlib
import json
import os

###############################################################################
# The JSON files of the project (silence.json, endpoints/*.json, tests/*.json):
# reading, writing and their version (etag), so that two clients (the admin
# panel and an editor) do not overwrite each other's changes.
###############################################################################

def etag_of(path):
    '''Version of a file: a hash of its content ("" if it does not exist)'''
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:16]


def read_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf8") as f:
        return json.load(f)


def write_json(path, data):
    '''Writes the file (or removes it if data is empty) and returns its new etag'''
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not data:
        if os.path.isfile(path):
            os.remove(path)
        return ""
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)
        f.write("\n")
    return etag_of(path)


def etags(folder):
    '''Etags of the JSON files of a folder, by name without .json'''
    if not os.path.isdir(folder):
        return {}
    return {f[:-5]: etag_of(os.path.join(folder, f))
            for f in sorted(os.listdir(folder)) if f.endswith(".json")}


def safe_name(name):
    '''A file or entry name without paths: letters, digits, _ and -'''
    name = (name or "").removesuffix(".json")
    if not name or not all(c.isalnum() or c in "_-" for c in name):
        raise ValueError(f"Invalid name '{name}'")
    return name
