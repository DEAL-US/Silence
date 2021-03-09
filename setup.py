import os
import re

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

# Borrowed from urllib3 (which is in turn borrowed from SQLAlchemy)
base_path = os.path.dirname(__file__)
ver_path = os.path.join(base_path, "silence", "__init__.py")

with open(ver_path, "r") as f:
    version = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S).match(f.read()).group(1)

setup(
    name="Silence",
    version=version,
    description="An educational API+Web framework.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/IISSI-US/Silence",
    author="Agustín Borrego",
    author_email="borrego@us.es",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "silence = silence.cli.manager:run_from_command_line",
        ],
    },
    install_requires=[
        "colorama~=0.4.3",
        "cryptography~=3.4.6",
        "Flask-Cors==3.0.8",
        "Flask==1.1.2",
        "itsdangerous~=1.1.0",
        "PyMySQL~=0.9.3",
        "pypika==0.37.7",
        "requests~=2.24.0",
        "Werkzeug~=1.0.1",
    ],
    python_requires="~=3.6",
    zip_safe=False
)