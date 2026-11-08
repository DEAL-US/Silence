import os

from silence.settings import settings

###############################################################################
# The molds of the code that Silence generates for the front-end (the JS API),
# brought by the project's template in .silence/<kind>/. Silence has no code of
# the front-end of its own: without molds, it is not generated. A mold is text
# with holes ({{name}}) that Silence fills in. See docs/molds.md.
###############################################################################

PROJECT_MOLDS = ".silence"


def molds_dir(kind):
    return os.path.join(settings.PROJECT_DIR, PROJECT_MOLDS, kind)


def has(kind, name):
    return os.path.isfile(os.path.join(molds_dir(kind), name))


def fill(kind, name, values, fallback=None):
    '''A mold with its holes filled in (fallback: the mold used if the project does not have this
    one, e.g., function_one.js → function.js)'''
    if fallback and not has(kind, name):
        name = fallback
    with open(os.path.join(molds_dir(kind), name), encoding="utf8") as f:
        text = f.read()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text
