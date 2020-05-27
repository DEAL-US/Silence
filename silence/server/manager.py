from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import NotFound

from silence.server.endpoint_loader import load_user_endpoints
from silence.settings import settings
from silence.exceptions import HTTPError

from os.path import join
from os import getcwd
import traceback

###############################################################################
# The server manager is responsible for setting up the Flask webserver,
# configuring it and deploying the endpoints and web app.
###############################################################################

static_folder = join(getcwd(), "docs") if settings.RUN_WEB else None
APP = Flask(__name__, static_folder=static_folder)

def setup():
    # Configures the web server
    APP.secret_key = settings.SECRET_KEY 
    APP.config["SESSION_TYPE"] = "filesystem"

    # Set up the error handle for our custom exception type
    @APP.errorhandler(HTTPError)
    def handle_HTTPError(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # Set up the generic Exception handler for server errors
    @APP.errorhandler(Exception)
    def handle_generic_error(exc):
        if isinstance(exc, HTTPError) or isinstance(exc, NotFound):
            # Handle these using the other function
            return exc
        
        exc_type = type(exc).__name__
        msg = str(exc)
        traceback.print_exc()
        err = HTTPError(500, msg, exc_type)
        return handle_HTTPError(err)

    # Load the user-provided API endpoints
    if settings.RUN_API:
        load_user_endpoints()

    # Load the web static files
    if settings.RUN_WEB:
        @APP.route("/")
        def root():
            return APP.send_static_file("index.html")

        @APP.route("/<path:path>")
        def other_path(path):
            return APP.send_static_file(path)



def run():
    APP.run(
        port=settings.HTTP_PORT,
        debug=settings.DEBUG_ENABLED,
    )
