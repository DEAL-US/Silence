from flask import Flask, jsonify

from silence.server.endpoint_loader import load_user_endpoints
from silence.settings import settings
from silence.exceptions import HTTPError

###############################################################################
# The server manager is responsible for setting up the Flask webserver,
# configuring it and deploying the endpoints and web app.
###############################################################################

APP = Flask(__name__)

def setup():
    # Configures the web server
    APP.secret_key = settings.SECRET_KEY 
    APP.config["SESSION_TYPE"] = "filesystem"

    # Set up the error handle for our custom exception type
    @APP.errorhandler(HTTPError)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # Load the user-provided endpoints
    load_user_endpoints()


def run():
    APP.run(
        port=settings.HTTP_PORT,
        debug=settings.DEBUG_ENABLED,
    )
