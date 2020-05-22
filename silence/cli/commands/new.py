from silence.settings import settings
from silence.cli.template_downloader import download_from_github

def handle(argv):
    project_name = argv[0] if len(argv) >= 1 else settings.PROJECT_TEMPLATE_NAME
    repo_url = argv[1] if len(argv) >= 2 else settings.PROJECT_TEMPLATE_REPO

    download_from_github(project_name, repo_url)

    print(f'The Silence project "{project_name}" has been created.')