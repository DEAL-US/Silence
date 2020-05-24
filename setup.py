from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name='Silence',
    version='0.0.2',
    description='An educational API+Web framework.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://github.com/agu-borrego/Silence',
    author='Agustín Borrego',
    author_email='borrego@us.es',
    license='MIT',
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "silence = silence.cli.manager:run_from_command_line",
        ],
    },
    install_requires=[
        'dload==0.6',
        'Flask==1.1.2',
        'PyMySQL==0.9.3',
    ],
    zip_safe=False
)