from silence.cli import template_downloader as tpl

###############################################################################
# silence list-templates: the templates and the admin panel of this version of
# Silence (its index, templates.json), with their versions.
###############################################################################

def handle(args):
    data = tpl.index()
    print("Templates of the frontend (silence new --template <name>):")
    for name, t in data["templates"].items():
        default = " (default)" if t.get("default") else ""
        local = " [local copy]" if tpl.local_source(tpl.parse_repo(t["repo"])[1]) else ""
        print(f"    · {name}{default} {t['version']}: {t.get('description', '')}{local}")
    admin = data["admin"]
    local = " [local copy]" if tpl.local_source(tpl.parse_repo(admin["repo"])[1]) else ""
    print(f"Admin panel: {admin['repo']} {admin['version']}{local}")
