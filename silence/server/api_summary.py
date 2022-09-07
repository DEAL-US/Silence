import re

from silence.logging.default_logger import logger
from silence.settings import settings

###############################################################################
# Utility class for printing the list of loaded endpoints
###############################################################################
class APISummary:
    def __init__(self):
        self.endpoints = []

    def register_endpoint(self, endpoint_data):
        self.endpoints.append(endpoint_data)

    def get_endpoint_list(self):
        return self.endpoints

    def print_endpoints(self):
        # Show a list of endpoints, sorted alphabetically
        if not self.endpoints:
            logger.info("No endpoints loaded.")
            return

        unique_endpoints = {}
        for endpoint in self.endpoints:
            route = endpoint["route"]
            unique_endpoints[route] = unique_endpoints.get(route, []) + [endpoint["method"]]

        unique_endpoints = list(unique_endpoints.items())
        unique_endpoints.sort(key=lambda x: x[0])

        host = settings.LISTEN_ADDRESS
        port = settings.HTTP_PORT
        base = f"http://{host}:{port}"

        logger.info("\nEndpoints loaded:")

        for route, method_list in unique_endpoints:
            # Force the GET-POST-PUT-DELETE order
            methods = "/".join([m for m in ("GET", "POST", "PUT", "DELETE") if m in method_list])
            # Replace $param with <param>
            route = re.sub(r"\$(\w+)", r"<\1>", route)

            logger.info("    · %s%s (%s)", base, route, methods)

        if unique_endpoints:
            # Add an empty line
            logger.info("")
    