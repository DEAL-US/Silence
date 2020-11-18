# Thanks to https://stackoverflow.com/a/3885198/5604339 :)
import decimal
import json

from silence.settings import settings

class DecimalFriendlyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            func = str if settings.DECIMALS_AS_STRINGS else float
            return func(o)
        return super(DecimalEncoder, self).default(o)

class DecimalFriendlySerializer:
    def dumps(o):
        return json.dumps(o, cls=DecimalFriendlyEncoder)

    def loads(s):
        return json.loads(s)