# 1.1.1-dev
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