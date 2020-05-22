from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name='Silence',
    version='0.0.1',
    description='An educational API+Web framework.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://github.com/IISSI-US/Silence',
    author='Agustín Borrego',
    author_email='borrego@us.es',
    license='MIT',
    packages=['silence'],
    entry_points={
        "console_scripts": [
            "silence = silence.cli.manager:run_from_command_line",
        ],
    },
    install_requires=[
        'certifi==2020.4.5.1',
        'chardet==3.0.4',
        'click==7.1.2',
        'dload==0.6',
        'Flask==1.1.2',
        'idna==2.9',
        'itsdangerous==1.1.0',
        'Jinja2==2.11.2',
        'MarkupSafe==1.1.1',
        'PyMySQL==0.9.3',
        'requests==2.23.0',
        'urllib3==1.25.9',
        'Werkzeug==1.0.1',
    ],
    zip_safe=False
)