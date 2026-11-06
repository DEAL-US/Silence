# Thanks to https://stackoverflow.com/a/3885198/5604339 :)
import decimal
import json

from flask.json.provider import DefaultJSONProvider

from silence.settings import settings

class SilenceJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            func = str if settings.DECIMALS_AS_STRINGS else float
            return func(o)
        elif hasattr(o, "isoformat"):
            # Dates, times and datetimes should be formatted following ISO-8601
            # with the format YYYY-MM-DD HH:MM:SS (or only the corresponding fragment
            # for dates and times)
            # ISO-8601 also defines "T" as a separator between date and time, which
            # we replace by a space for compatibility with MySQL
            # Instead of checking directly for their types, we test whether they
            # have the isoformat() method, which all date/time classes share
            return o.isoformat().replace("T", " ")

        try:
            return super().default(o)
        except TypeError:
            return str(o)

class SilenceJSONProvider(DefaultJSONProvider):
    '''Flask 3 JSON provider that serializes like SilenceJSONEncoder'''
    def dumps(self, obj, **kwargs):
        kwargs.setdefault("sort_keys", self.sort_keys)
        kwargs.setdefault("ensure_ascii", self.ensure_ascii)
        return json.dumps(obj, cls=SilenceJSONEncoder, **kwargs)

class SilenceJSONSerializer:
    def dumps(o):
        return json.dumps(o, cls=SilenceJSONEncoder)

    def loads(s):
        return json.loads(s)