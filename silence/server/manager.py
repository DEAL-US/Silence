from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import click

from silence.server.endpoint_loader import load_user_endpoints, load_default_endpoints
from silence.settings import settings
from silence.exceptions import HTTPError
from silence.logging.default_logger import logger
from silence.logging.flask_filter import FlaskFilter
from silence.utils.silence_json_encoder import SilenceJSONEncoder
from silence.server.api_summary import APISummary

from os.path import join
from os import getcwd
import traceback
import mimetypes
import logging

###############################################################################
# The server manager is responsible for setting up the Flask webserver,
# configuring it and deploying the endpoints and web app.
###############################################################################

static_folder = join(getcwd(), "web") if settings.RUN_WEB else None
APP = Flask(__name__, static_folder=static_folder)
cors = CORS(APP, resources={f"{settings.API_PREFIX}*": {"origins": "*"}})
API_SUMMARY = APISummary()

def setup():
    # Configures the web server
    APP.secret_key = settings.SECRET_KEY 
    APP.config["SESSION_TYPE"] = "filesystem"
    APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = settings.HTTP_CACHE_TIME 

    # Mute Flask's startup messages
    def noop(*args, **kwargs): pass
    click.echo = noop
    click.secho = noop

    # Add our Flask filter to customize Flask logging messages
    logging.getLogger("werkzeug").addFilter(FlaskFilter())

    # Override the default JSON encoder so that it works with the Decimal type
    APP.json_encoder = SilenceJSONEncoder

    # Manually set up the MIME type for .js files
    # This patches a known issue on Windows, where the MIME type for JS files
    # is sometimes incorrectly set to text/plain in the registry
    mimetypes.add_type("application/javascript", ".js", strict=True)

    # Set up the error handle for our custom exception type
    @APP.errorhandler(HTTPError)
    def handle_HTTPError(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # Set up the generic Exception handler for server errors
    @APP.errorhandler(Exception)
    def handle_generic_error(exc):
        # Pass through our own HTTP error exception
        if isinstance(exc, HTTPError):
            return exc

        # Create a similar JSON response for Werkzeug's exceptions
        if isinstance(exc, HTTPException):
            code = exc.code
            res = jsonify({"message": exc.description, "code": code})
            return res, code
        
        # We're facing an uncontrolled server exception
        logger.exception(exc)

        exc_type = type(exc).__name__
        msg = str(exc)
        err = HTTPError(500, msg, exc_type)
        return handle_HTTPError(err)

    # Load the user-provided API endpoints and the default ones
    if settings.RUN_API:
        load_default_endpoints()
        # create_entity_endpoints()
        load_user_endpoints()

        if settings.SHOW_ENDPOINT_LIST:
            API_SUMMARY.print_endpoints()

    # Load the web static files
    if settings.RUN_WEB:
        logger.debug("Setting up web server")
        @APP.route("/")
        def root():
            return APP.send_static_file("index.html")

        @APP.route("/<path:path>")
        def other_path(path):
            return APP.send_static_file(path)

def run():
    APP.run(
        host=settings.LISTEN_ADDRESS,
        port=settings.HTTP_PORT,
        debug=settings.DEBUG_ENABLED,
        threaded=True,
    )
