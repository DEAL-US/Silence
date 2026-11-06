import sys
from silence.logging.default_logger import logger
from traceback import print_exc

import test_summary
import test_register
import test_login
import test_roles
import test_banned
import test_loggedId
import test_departments
import test_employees

# Order is important!
tests = [
    test_summary,
    test_register,
    test_login,
    test_roles,
    test_banned,
    test_loggedId,
    test_departments,
    test_employees,
]

failed_tests = []

for test in tests:
    try:
        test.run()
    except AssertionError:
        print_exc()
        logger.error(f"{test.__name__} failed. Proceeding with the next one.")
        failed_tests.append(test.__name__)

if failed_tests:
    logger.error(f"The following tests failed: {', '.join(failed_tests)}. Exiting with error code.")

exit_code = 0 if not failed_tests else 1
sys.exit(exit_code)