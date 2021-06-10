from silence.server.endpoint_creator import create_api
from silence.settings import settings

def handle(args):
    if(settings.ENABLE_ENDPOINT_AUTO_GENERATION):
        print("Creating the default endpoints and generating the api files...")
        create_api()
        print("Done!")
    else:
        print("Endpoint auto generation is disabled in the settings, you need to enable before you can use this command.")