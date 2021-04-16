# 1.2.2-dev
- Changed the serialization of datetime objects to follow ISO 8601.
- Set the MIME type of `.js` files to `application/javascript` manually, to prevent the wrong type from being dispatched due to bad configurations of the Windows registry.

# 1.2.2
- Added a new `HTTP_CACHE_TIME` setting to control caching of static web files. Defaults to 0 for easier development, which means that all static files (HTML, JS, CSS...) are not cached by web browsers.
- The list of all loaded endpoints is now displayed when using `silence new`. Added a new `SHOW_ENDPOINT_LIST` setting to disable this behavior.
- The `SECRET_KEY` is now changed in-place when creating a project from a repo URL if it already exists, instead of always adding it in a new line with the info comments.

# 1.2.1
- Added `cryptography` to dependencies for compatibility with MySQL.

# 1.2.0
- Improvements to `silence new`:
    - It now requires a project name, i.e., you cannot use `silence new` without at least one argument.
    - It downloads a certain template by default, right now, 'employees'.
    - A different template can be specified using the `--template` argument.
    - A GitHub repo URL can be provided using the `--url` argument. Note that `--template` and `--url` are mutually exclusive.
    - The `--blank` parameter is provided as a shorthand for `--template blank`.
    - It now removes any `.gitkeep` files found in the downloaded project.
    - If a `SECRET_KEY` is already set for the downloaded project, `silence new` deletes it and provides a new, randomly generated one.
    - A warning is issued if a `settings.py` file cannot be found in the downloaded project.
    - It automatically determines the default branch name for the repository to download, instead of assuming "master" (yes, I'm looking at you, "main").
- A new command, `silence list-templates`, retrieves the list of existing project templates.
- Minor: Vectorized logo shown in README.md.

# 1.1.2
- Set the default address for the webserver to `127.0.0.1` instead of `0.0.0.0`
- Removed the default `SECRET_KEY`, it is now always required to provide one

# 1.1.1
- Updated README
- Fixed 500 errors when simplejson was installed alongside Silence
- Fixed SQL params not always being filled correctly in GET requests if more than one param is used

# 1.1.0
- Added a check for new Silence versions when using `silence run`, and a `CHECK_FOR_UPDATES` configuration parameter to opt out of this check
- Add support for storing the endpoint files in a folder named `endpoints/` instead of `api/`. The support for an `api/` folder will be dropped in the future.
- Display a warning message if endpoints are found in the `api/` folder instead of `endpoints/`

# 1.0.7
- Fixed encoding errors that resulted in 500 errors
- The endpoint loader now doesn't try to load non-Python files, which resulted in a fatal error

# 1.0.6
- Fixed compatibility with DECIMAL columns
- Added a new `-v`/`--version` command

# 1.0.5
- Fixed a bug where `silence createdb` wouldn't work for certain database names

# 1.0.4
- Added logo and updated README
- Added `ENABLE_SUMMARY` and `COLORED_OUTPUT` configuration parameters

# 1.0.3
- Changed repo ownership

# 1.0.2
- Fixed a bug where the template project couldn't be downloaded if Silence wasn't installed inside a virtualenv

# 1.0.1
- Fixed a bug where ordering didn't work properly for non-string fields

# 1.0.0
- First release!

# 0.4.3
- Removed the API tree on startup since it could cause issues
- API calls that perform update operations now return the last modified ID in a JSON response
- Proper README

# 0.4.2
- Added a summary of API endpoints with their descriptions in the base URL
- Automatic column name casing for the login and register endpoints

# 0.4.1
- Display the API structure as a tree during startup
- Run server on all network interfaces
- Automatically set up a permissive CORS setting

# 0.4.0
- Added support for application/json as encoding for POST/PUT requests
- Added configuration options to disable login and register
- Custom formatting for HTTP log messages
- Use a connection pool to connect to the DB

# 0.3.0
- Added support for the default endpoints /login and /register using custom tables and fields
- Added support for session tokens and authentication requirements

# 0.2.0
- Added support for HTTP POST/PUT/DELETE and SQL INSERT/UPDATE/DELETE
- Added support for static web files

# 0.1.0
- Added support for HTTP GET / SQL SELECT (URL params, query filtering...)

# 0.0.5
- Improvements in version handling

# 0.0.4
- Improvements in GitHub automated actions

# 0.0.3
- Fixing the PyPI publication workflow
- Added PyPI badge in README
- Specified minimum Python version in setup.py

# 0.0.2
- Continuous integration and deployment using Travis and GitHub actions
- Fixed a wrong link in setup.py
- Minimized the number of dependencies

# 0.0.1
- Initial version, work in progress