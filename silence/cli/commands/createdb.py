from silence.db.populate import create_database

def handle(argv):
    print("Creating the database...")
    create_database()
    print("Done!")