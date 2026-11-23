"""Passenger entry point for WaRa BD (cPanel → "Setup Python App").

In cPanel set:
    Application root:          the folder that holds this file and manage.py
    Application startup file:  passenger_wsgi.py
    Application Entry point:   application

The settings come from the .env file next to this file (copy .env.example to
.env and fill in the server values: DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS,
DJANGO_SITE_URL, DJANGO_DB_*, …).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# The project folder, and rizz/ (it holds the "users" app).
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "rizz"))

# Read .env and use the production settings (both can still be overridden
# by environment variables set in cPanel).
os.environ.setdefault("DJANGO_READ_DOT_ENV_FILE", "True")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# MySQL driver: mysqlclient if the server could build it, otherwise PyMySQL
# (pip install PyMySQL) — many shared hosts cannot compile mysqlclient.
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

from config.wsgi import application  # noqa: E402,F401
