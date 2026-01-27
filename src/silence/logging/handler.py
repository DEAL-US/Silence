from silence.settings import settings

from logging import StreamHandler
import threading
import platform

class MaybeBlockingHandler(StreamHandler):
    def __init__(self):
        super().__init__()

        # This is done to prevent colored log messages from overlapping
        # when running on Windows. This happens because stdout in Windows
        # must be flushed after every color change, which sometimes makes
        # colored log messages overlap.
        if settings.COLORED_OUTPUT and platform.system() == "Windows":
            self._write_lock = threading.Lock() 
        else:
            # Otherwise, we use a dummy "Lock" that does nothing
            self._write_lock = NoopLock()

    def emit(self, record):
        with self._write_lock:
            super().emit(record)

# A dummy "Lock" that does nothing when it is acquired and released using "with"
class NoopLock:
    def __enter__(self, *args, **kwargs): pass
    def __exit__(self, *args, **kwargs): pass
