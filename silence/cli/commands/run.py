from silence.server import manager as server_manager

def handle(argv):
    server_manager.setup()
    server_manager.run()