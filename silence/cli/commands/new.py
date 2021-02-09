from silence.settings import settings
from silence.cli.template_downloader import download_from_github

def handle(args):
    args = vars(args)  # Convert the Namespace object into a dict

    if all(not args[k] for k in ("blank", "url", "template")):
        # No extra args provided, use the default template
        args["template"] = settings.DEFAULT_TEMPLATE_NAME
    elif args["blank"]:
        args["template"] = "blank"

    template = args["template"]
    project_name = args["name"]

    if template:
        repo_url = f"https://github.com/{settings.GITHUB_TEMPLATES_OWNER}/silence-template-{template}"
    else:
        # We have to download a repo from a URL
        repo_url = args["url"]

    download_from_github(project_name, repo_url)
    extra_text = f"using the template '{template}'" if template else "from the provided URL"
    print(f'The Silence project "{project_name}" has been created {extra_text}.')