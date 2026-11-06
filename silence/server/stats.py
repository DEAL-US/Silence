import threading
import time

###############################################################################
# Request statistics, kept in memory (nothing is written in the project).
# Three groups: "silence" (login, register, summary), "api" (the student's
# endpoints) and "web" (the student's static files). The admin panel's own
# requests are not counted.
###############################################################################

GROUPS = ("silence", "api", "web")

_lock = threading.Lock()
_started = time.time()
_data = {g: {} for g in GROUPS}


def record(group, key, status, elapsed_ms):
    with _lock:
        entry = _data[group].setdefault(key, {"count": 0, "errors": 0, "status": {}, "totalMs": 0.0})
        entry["count"] += 1
        entry["totalMs"] += elapsed_ms
        entry["status"][str(status)] = entry["status"].get(str(status), 0) + 1
        if status >= 400:
            entry["errors"] += 1


def snapshot():
    with _lock:
        res = {"since": _started, "groups": {}}
        for group, entries in _data.items():
            rows = [{"key": k, "count": e["count"], "errors": e["errors"], "status": dict(e["status"]),
                     "avgMs": round(e["totalMs"] / e["count"], 1)} for k, e in entries.items()]
            rows.sort(key=lambda r: -r["count"])
            res["groups"][group] = {"total": sum(r["count"] for r in rows), "entries": rows}
        return res


def reset():
    global _started
    with _lock:
        for group in GROUPS:
            _data[group].clear()
        _started = time.time()
