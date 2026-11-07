import sys

from silence.logging.default_logger import logger
from silence.settings import settings, PROJECT_FILE
from silence.logging.utils import COLORS, RESET

###############################################################################
# silence test [name...]: runs the project's tests (tests/*.json), each one
# inside a transaction that is rolled back. The exit code is 1 if any fails.
###############################################################################

def handle(args):
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project.", PROJECT_FILE)
        sys.exit(1)

    settings.require_valid()
    from silence.server import manager as server_manager
    from silence.testing import runner, model

    server_manager.setup()
    suite = model.load_tests()
    for err in suite.errors:
        logger.error("Test error: %s", err)

    names = args.names or None
    results = runner.run_tests(suite, names)
    passed = sum(1 for r in results if r["passed"])

    for r in results:
        mark = f"{COLORS['GREEN']}PASS{RESET}" if r["passed"] else f"{COLORS['RED']}FAIL{RESET}"
        logger.info("%s  %s (%s)", mark, r["name"], r["file"])
        if not r["passed"]:
            for step in r["steps"]:
                if not step["passed"]:
                    logger.info("        step %d: %s %s -> %s", step["index"] + 1, step["method"],
                                step["path"], "; ".join(step["failures"]))

    color = COLORS["GREEN"] if passed == len(results) and not suite.errors else COLORS["RED"]
    logger.info("\n%s%d of %d tests passed%s", color, passed, len(results), RESET)
    sys.exit(0 if passed == len(results) and not suite.errors else 1)
