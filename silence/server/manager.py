import json
import mimetypes
import logging
import os
import time
from datetime import datetime

from flask import Flask, jsonify, request, g, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, NotFound

from silence.settings import settings
from silence.exceptions import HTTPError
from silence.logging.default_logger import logger
from silence.logging.utils import COLORS, RESET
from silence.utils.silence_json_encoder import SilenceJSONProvider
from silence.server import stats
from silence.server.endpoints import REGISTRY, run as run_endpoint
from silence.server import auth_endpoints

###############################################################################
# The server manager sets up the Flask web server: the API (a single
# dispatcher over the endpoint registry, so that the changes made in the
# admin panel take effect without restarting), the web app and the panel.
###############################################################################

APP = Flask(__name__, static_folder=None)
CORS(APP, resources={r"/api/*": {"origins": "*"}})
APP.json = SilenceJSONProvider(APP)

# Manually set up the MIME type for .js files (wrong in some Windows registries)
mimetypes.add_type("application/javascript", ".js", strict=True)

API_METHODS = ["GET", "POST", "PUT", "DELETE"]


def web_dir():
    return os.path.join(settings.PROJECT_DIR, "web")


def is_api_path(path):
    prefix = settings.API_PREFIX
    return path == prefix or path.startswith(prefix + "/")


def is_admin_path(path):
    '''The admin panel (/admin) and the admin API (/_silence): neither logged nor counted'''
    return path in ("/admin", "/_silence") or path.startswith(("/admin/", "/_silence/"))


###############################################################################
# API
###############################################################################

def api_summary():
    '''GET <prefix>: the list of loaded endpoints'''
    eps = [{"route": settings.API_PREFIX + e.route, "method": e.method, "description": e.description}
           for e in REGISTRY.endpoints]
    if settings.ENABLE_LOGIN:
        eps.append({"route": settings.API_PREFIX + "/login", "method": "POST", "description": "Logs in"})
    if settings.ENABLE_REGISTER:
        eps.append({"route": settings.API_PREFIX + "/register", "method": "POST", "description": "Registers a user"})
    return eps


def dispatch(path):
    method = request.method.upper()
    sub = "/" + path.strip("/") if path else ""

    if sub == "" and method == "GET":
        g.stats_group, g.stats_key = "silence", "GET " + settings.API_PREFIX
        return jsonify(api_summary()), 200
    if sub == "/login" and method == "POST" and settings.ENABLE_LOGIN:
        g.stats_group, g.stats_key = "silence", "POST /login"
        res, status = auth_endpoints.login()
        return jsonify(res), status
    if sub == "/register" and method == "POST" and settings.ENABLE_REGISTER:
        g.stats_group, g.stats_key = "silence", "POST /register"
        res, status = auth_endpoints.register()
        return jsonify(res), status

    ep, url_params = REGISTRY.match(method, sub)
    if ep is None:
        g.stats_group, g.stats_key = "api", f"{method} (no endpoint)"
        if REGISTRY.route_exists(sub):
            raise HTTPError(405, f"{method} is not allowed on {settings.API_PREFIX}{sub}")
        raise HTTPError(404, f"There is no endpoint {method} {settings.API_PREFIX}{sub}")

    g.stats_group, g.stats_key = "api", f"{ep.method} {ep.route}"
    res, status = run_endpoint(ep, url_params)
    return jsonify(res), status


def register_api_routes():
    prefix = settings.API_PREFIX
    APP.add_url_rule(prefix, "api_root", lambda: dispatch(""), methods=API_METHODS)
    APP.add_url_rule(prefix + "/<path:path>", "api", dispatch, methods=API_METHODS)


###############################################################################
# Web app (web/ folder)
###############################################################################

def serve_web(path="index.html"):
    g.stats_group, g.stats_key = "web", "/" + path
    folder = web_dir()
    full = os.path.join(folder, path)
    if os.path.isdir(full):
        path = os.path.join(path, "index.html")
    try:
        response = send_from_directory(folder, path, max_age=settings.HTTP_CACHE_TIME)
    except NotFound:
        if path == "favicon.ico" and os.path.isfile(os.path.join(folder, "images", "favicon.ico")):
            return send_from_directory(os.path.join(folder, "images"), "favicon.ico")
        if path == "index.html" and not os.path.isfile(full):
            return ("<!doctype html><title>Silence</title><p>This project has no "
                    "<code>web/index.html</code> yet. Open the <a href='/admin/'>admin panel</a>.</p>"), 200
        if "text/html" in request.headers.get("Accept", ""):
            return (f"<!doctype html><title>Not found</title><h1>Not found</h1>"
                    f"<p>There is no file <code>web/{path}</code> in this project.</p>"), 404
        raise
    return response


def register_web_routes():
    APP.add_url_rule("/", "web_root", serve_web)
    APP.add_url_rule("/<path:path>", "web", serve_web)


###############################################################################
# Admin panel: the project's admin/ folder, if it has one (Silence does not
# know what it contains: it is an app that uses the admin API)
###############################################################################

def admin_dir():
    return os.path.join(settings.PROJECT_DIR, "admin")


def serve_admin(path="index.html"):
    folder = admin_dir()
    if not os.path.isdir(folder):
        return ("<!doctype html><title>Silence</title><p>This project has no admin panel "
                "(<code>admin/</code> folder). Add it with <code>silence admin update</code>.</p>"), 404
    if path.endswith("/") or os.path.isdir(os.path.join(folder, path)):
        path = os.path.join(path, "index.html")
    return send_from_directory(folder, path, max_age=0)


def register_admin_routes():
    from silence.manage.api import manage
    APP.register_blueprint(manage)
    APP.add_url_rule("/admin/", "admin_root", serve_admin)
    APP.add_url_rule("/admin/<path:path>", "admin", serve_admin)


###############################################################################
# Errors, logs and statistics
###############################################################################

@APP.errorhandler(HTTPError)
def handle_http_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@APP.errorhandler(Exception)
def handle_generic_error(exc):
    if isinstance(exc, HTTPError):
        return handle_http_error(exc)
    if isinstance(exc, HTTPException):
        return jsonify({"message": exc.description, "code": exc.code}), exc.code

    if settings.DEBUG_ENABLED:
        logger.exception(exc)
    else:
        logger.error("%s: %s (enable debug mode to see the full stack trace)", type(exc).__name__, exc)
    return handle_http_error(HTTPError(500, str(exc), type(exc).__name__))


@APP.before_request
def start_timer():
    g.start = time.perf_counter()


@APP.after_request
def log_and_count(response):
    path = request.path
    if is_admin_path(path) or request.headers.get("X-Silence-Test"):
        return response  # The admin panel and the tests are neither logged nor counted

    elapsed = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
    group = g.get("stats_group") or ("api" if is_api_path(path) else "web")
    key = g.get("stats_key") or path
    stats.record(group, key, response.status_code, elapsed)

    code = response.status_code
    code_color = COLORS["GREEN"] if code < 400 else COLORS["YELLOW"] if code < 500 else COLORS["RED"]
    kind, kind_color = ("[WEB]", COLORS["CYAN"]) if group == "web" else ("[API]", COLORS["MAGENTA"])
    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"{date} | {kind_color}{kind}{RESET} {request.method} {request.full_path.rstrip('?')} - {code_color}{code}{RESET}"
    if code >= 400 and response.is_json:
        msg = (response.get_json(silent=True) or {}).get("message")
        if msg:
            line += f" {msg}"
    logger.info(line)
    if settings.LOG_BODIES and request.method in ("POST", "PUT") and group != "web":
        body = logged_body()
        if body:
            logger.info(f"{' ' * 22}{COLORS['YELLOW']}body{RESET} {body}")
    return response


def logged_body(max_chars=300):
    '''The body of the request for the console, without passwords'''
    data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    if not isinstance(data, dict) or not data:
        return ""
    hidden = {"password"}
    if settings.AUTH_LINKED:
        hidden.add(settings.USER_AUTH_DATA["password"].lower())
    shown = {k: ("***" if k.lower() in hidden else v) for k, v in data.items()}
    text = json.dumps(shown, ensure_ascii=False, default=str)
    return text if len(text) <= max_chars else text[:max_chars] + "…"


###############################################################################
# Setup and run
###############################################################################

_routes_registered = False

def setup():
    '''Loads the endpoints and registers the routes (once)'''
    global _routes_registered
    APP.secret_key = settings.SECRET_KEY
    APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = settings.HTTP_CACHE_TIME

    # Werkzeug's own request log is replaced by ours (log_and_count)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    REGISTRY.load().log_errors()

    if not _routes_registered:
        register_admin_routes()
        register_api_routes()
        register_web_routes()
        _routes_registered = True
    return APP


def print_endpoints():
    base = f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}"
    if not REGISTRY.endpoints:
        logger.info("No endpoints loaded: generate them in the admin panel.")
        return
    logger.info("\nEndpoints loaded:")
    for ep in sorted(REGISTRY.endpoints, key=lambda e: (e.route, API_METHODS.index(e.method))):
        logger.info("    · %-6s %s%s%s", ep.method, base, settings.API_PREFIX, ep.route.replace("$", ":"))
    logger.info("")


def run():
    APP.run(host=settings.LISTEN_ADDRESS, port=settings.HTTP_PORT,
            debug=False, threaded=True, use_reloader=False)
