import sys

# Replaces the current Silence version with the one provided as a command line argument.
# Then, to publish it: commit, tag it (git tag -a vX.Y.Z), push the branch silence3 and the tag, and
# move the branch stable to it (git push deal vX.Y.Z^{commit}:refs/heads/stable), which is what
# the README and the wiki install (and what Silence checks for updates)
if len(sys.argv) < 2:
    print("Usage: bump_version.py <version>")
    exit(1)

version = sys.argv[1]

# Write the version to __init__.py and to the top of the changelog
open("silence/__init__.py", "w").write(f'__version__ = "{version}"\n')

changelog_lines = open("CHANGELOG.md", "r").readlines()
changelog_lines[0] = f"# {version}\n"
open("CHANGELOG.md", "w").writelines(changelog_lines)
