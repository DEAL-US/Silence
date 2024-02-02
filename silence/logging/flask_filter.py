from silence.logging import utils

import logging

###############################################################################
# Filters and modifies Flask's log records in-place
###############################################################################

class FlaskFilter(logging.Filter):

    def filter(self, record):
        record = utils.format_flask_record(record)

        if record == "running_msg":
            return True
        
        
        # Pass it on to Silence's logger, which implements
        # blocking to prevent multiple lines from overlapping,
        # and filter it out from this one
        logging.getLogger("silence").handle(record)
        return False