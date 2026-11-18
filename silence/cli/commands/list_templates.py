from silence.cli import template_downloader as tpl

###############################################################################
# silence list-templates: the templates and the admin panel of this version of
# Silence (its index, templates.json), with their versions: "latest" (the latest
# published one) and the one tested with this Silence.
###############################################################################

def version(entry):
    '''"latest (tested v1.4.0)", or the fixed version'''
    tested = entry.get("tested")
    return f"{entry['version']} (tested {tested})" if entry["version"] == tpl.LATEST and tested else entry["version"]


def handle(args):
    data = tpl.index()
    print("Templates of the frontend (silence new --template <name>):")
    for name, t in data["templates"].items():
        default = " (default)" if t.get("default") else ""
        local = " [local copy]" if tpl.local_source(tpl.parse_repo(t["repo"])[1]) else ""
        print(f"    · {name}{default} {version(t)}: {t.get('description', '')}{local}")
    admin = data["admin"]
    local = " [local copy]" if tpl.local_source(tpl.parse_repo(admin["repo"])[1]) else ""
    print(f"Admin panel: {admin['repo']} {version(admin)}{local}")
