import threading
import time

###############################################################################
# Request statistics, kept in memory (nothing is written in the project), in
# three groups, as Silence of Rust (silence-dev4) shows them:
#   "api":     the student's endpoints (endpoints/*.json), by endpoint
#   "silence": the endpoints that Silence gives to the student's app: login,
#              register and the API summary (GET /api)
#   "web":     the files of web/ (the app that the student develops), by file
# The requests of the tests count too; the admin panel (its files and the admin
# API, /_silence/v1) does not: only the traffic of the student's app.
###############################################################################

_lock = threading.Lock()
_started = time.time()

KINDS = {"html": "page", "htm": "page", "css": "style", "js": "script", "mjs": "script", "json": "data",
         "png": "image", "jpg": "image", "jpeg": "image", "gif": "image", "svg": "image", "webp": "image",
         "ico": "image", "woff": "font", "woff2": "font", "ttf": "font"}


def _api_group():
    return {"requests": 0, "errors": 0, "totalMs": 0.0, "byMethod": {}, "byStatus": {}, "endpoints": {},
            "unmatched": {}}


_data = {"api": _api_group(), "silence": _api_group(),
         "web": {"requests": 0, "notFound": 0, "bytes": 0, "byKind": {}, "files": {}}}


def file_kind(path):
    ext = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else "html"
    return KINDS.get(ext, "other")


def record_api(group, method, key, status, elapsed_ms, matched=True):
    '''A request to the student's API ("api") or to Silence's ("silence"); key: the endpoint'''
    with _lock:
        g = _data[group]
        g["requests"] += 1
        g["totalMs"] += elapsed_ms
        g["byMethod"][method] = g["byMethod"].get(method, 0) + 1
        g["byStatus"][str(status)] = g["byStatus"].get(str(status), 0) + 1
        if status >= 400:
            g["errors"] += 1
        if not matched:
            g["unmatched"][key] = g["unmatched"].get(key, 0) + 1
            return
        e = g["endpoints"].setdefault(key, {"requests": 0, "errors": 0, "totalMs": 0.0, "maxMs": 0.0, "byStatus": {}})
        e["requests"] += 1
        e["totalMs"] += elapsed_ms
        e["maxMs"] = max(e["maxMs"], elapsed_ms)
        e["byStatus"][str(status)] = e["byStatus"].get(str(status), 0) + 1
        if status >= 400:
            e["errors"] += 1


def record_web(path, status, size):
    with _lock:
        w = _data["web"]
        kind = file_kind(path)
        w["requests"] += 1
        w["byKind"][kind] = w["byKind"].get(kind, 0) + 1
        f = w["files"].setdefault(path, {"kind": kind, "requests": 0, "notFound": 0, "bytes": 0})
        f["requests"] += 1
        if status == 404:
            w["notFound"] += 1
            f["notFound"] += 1
        else:
            w["bytes"] += size
            f["bytes"] += size


def _api_report(g):
    endpoints = []
    for key, e in g["endpoints"].items():
        method, _, route = key.partition(" ")
        endpoints.append({"method": method, "route": route, "requests": e["requests"], "errors": e["errors"],
                          "byStatus": dict(e["byStatus"]), "avgMs": round(e["totalMs"] / e["requests"], 1),
                          "maxMs": round(e["maxMs"], 1)})
    endpoints.sort(key=lambda e: -e["requests"])
    return {"requests": g["requests"], "errors": g["errors"],
            "avgMs": round(g["totalMs"] / g["requests"], 1) if g["requests"] else 0,
            "byMethod": dict(g["byMethod"]), "byStatus": dict(g["byStatus"]),
            "endpoints": endpoints, "unmatched": dict(g["unmatched"])}


def snapshot():
    with _lock:
        w = _data["web"]
        files = [{"path": p, **f} for p, f in w["files"].items()]
        files.sort(key=lambda f: -f["requests"])
        return {"since": _started, "api": _api_report(_data["api"]), "silence": _api_report(_data["silence"]),
                "web": {"requests": w["requests"], "notFound": w["notFound"], "bytes": w["bytes"],
                        "byKind": dict(w["byKind"]), "files": files}}


def reset():
    global _started
    with _lock:
        _data["api"] = _api_group()
        _data["silence"] = _api_group()
        _data["web"] = {"requests": 0, "notFound": 0, "bytes": 0, "byKind": {}, "files": {}}
        _started = time.time()
