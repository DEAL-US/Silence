import sys

# Replaces the current Silence version with the one provided as a command line argument
if len(sys.argv) < 2:
    print("Usage: bump_version.py <version>")
    exit(1)

version = sys.argv[1]

# Write the version to __init__.py and to the top of the changelog
open("silence/__init__.py", "w").write(f'__version__ = "{version}"\n')

changelog_lines = open("CHANGELOG.md", "r").readlines()
changelog_lines[0] = f"# {version}\n"
open("CHANGELOG.md", "w").writelines(changelog_lines)
