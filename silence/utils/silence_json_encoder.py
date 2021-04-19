# Thanks to https://stackoverflow.com/a/3885198/5604339 :)
import decimal
from flask import json
from datetime import datetime

from silence.settings import settings

class SilenceJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            func = str if settings.DECIMALS_AS_STRINGS else float
            return func(o)
        elif isinstance(o, datetime):
            return o.isoformat()

        try:
            return super().default(o)
        except TypeError:
            return str(o)

class SilenceJSONSerializer:
    def dumps(o):
        return json.dumps(o, cls=SilenceJSONEncoder)

    def loads(s):
        return json.loads(s)