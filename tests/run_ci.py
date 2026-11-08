"""Runs the CI tests of Silence on tests/ci_project.

1. Copies the project to a temporary folder and sets its database from the
   environment (SILENCE_DB_HOST, SILENCE_DB_PORT, SILENCE_DB_USER,
   SILENCE_DB_PASSWORD, SILENCE_DB_NAME), by default the local one.
2. Loads the database with the scripts of sql/ (Silence 3 does not run them).
3. Starts 'silence run' and runs the API tests of test/ (inherited from the
   Silence-CI-Project of Silence 2, adapted where Silence 3 changes on purpose).
4. Reloads the database and runs the unit tests of tests/*.json through HTTP
   (run_units.py, as the admin panel does: Silence does not run tests).

Exit code 0 only if everything passes.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(HERE, "ci_project")
# The silence of this Python environment (not another one in the PATH, e.g., the Rust one)
SILENCE = os.path.join(os.path.dirname(sys.executable), "silence")
if not os.path.isfile(SILENCE):
    SILENCE = shutil.which("silence")


def db_settings():
    with open(os.path.join(PROJECT, "silence.json"), encoding="utf8") as f:
        db = json.load(f)["database"]
    env = os.environ
    return {"host": env.get("SILENCE_DB_HOST", db["host"]), "port": int(env.get("SILENCE_DB_PORT", db["port"])),
            "user": env.get("SILENCE_DB_USER", db["user"]), "password": env.get("SILENCE_DB_PASSWORD", db["password"]),
            "name": env.get("SILENCE_DB_NAME", db["name"])}


def load_database(project):
    '''The database created again with the scripts of database.scripts (silence createdb)'''
    if subprocess.run([SILENCE, "createdb"], cwd=project).returncode != 0:
        raise SystemExit("The database could not be created")


def free_port():
    '''A free port, so as not to test another Silence that is running (e.g., on 8080)'''
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(url, process, seconds=20):
    for _ in range(seconds * 4):
        if process.poll() is not None:
            return False  # Our Silence has stopped (e.g., the port is in use)
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    db = db_settings()
    work = tempfile.mkdtemp(prefix="silence-ci-")
    project = os.path.join(work, "ci_project")
    shutil.copytree(PROJECT, project)
    path = os.path.join(project, "silence.json")
    with open(path, encoding="utf8") as f:
        data = json.load(f)
    data["database"].update(db)
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)

    try:
        return run(project)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(project):
    load_database(project)
    port = free_port()
    server = subprocess.Popen([SILENCE, "run", "--no-browser", "--port", str(port)], cwd=project)
    try:
        if not wait_for(f"http://127.0.0.1:{port}/api", server):
            print("Silence did not start")
            return 1
        env = {**os.environ, "SILENCE_CI_BASE_URL": f"http://127.0.0.1:{port}/api"}
        api = subprocess.run([sys.executable, "run_tests.py"], cwd=os.path.join(project, "test"), env=env).returncode
        # The unit tests change the database: they start from the original data
        load_database(project)
        tests = subprocess.run([sys.executable, os.path.join(HERE, "run_units.py"),
                                f"http://127.0.0.1:{port}"]).returncode
    finally:
        server.terminate()
        server.wait()
    print(f"\nAPI tests: {'OK' if api == 0 else 'FAILED'}; unit tests: {'OK' if tests == 0 else 'FAILED'}")
    return 0 if api == 0 and tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
