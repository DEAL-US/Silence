from flask import Flask

from silence.server.endpoint_loader import load_user_endpoints
from silence.settings import settings

###############################################################################
# The server manager is responsible for setting up the Flask webserver,
# configuring it and deploying the endpoints and web app.
###############################################################################

APP = Flask(__name__)

def setup():
    # Configures the web server
    APP.secret_key = settings.SECRET_KEY 
    APP.config["SESSION_TYPE"] = "filesystem"

    load_user_endpoints()

    # TO-DO remove this later
    @APP.route("/test")
    def test():
        return "Hola! :D"


def run():
    
    APP.run(
        port=settings.HTTP_PORT,
        debug=settings.DEBUG_ENABLED,
    )
    