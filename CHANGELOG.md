# 0.4.2-dev
- Removed the API tree on startup since it could cause issues
- API calls that perform update operations now return the last modified ID in a JSON response

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