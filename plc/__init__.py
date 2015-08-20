"""
The PLC Python library.
"""
__version__ = '0.1.5'
AUTHOR = "Piotr Wilkosz"
EMAIL = "Piotr.Wilkosz@gmail.com"
NAME = "ProdLineTrace"

import logging
from plc.helpers import parse_config, parse_args
from constants import SQLALCHEMY_DATABASE_URI_PREFIX
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)

_opts, _args = parse_args()
_config = {}
try:
    _config['dbfile'] = parse_config(_opts.config)['main']['dbfile'][0]
except Exception, e:
    _config['dbfile'] = 'plc.db'

db_connection_string = SQLALCHEMY_DATABASE_URI_PREFIX + _config['dbfile']

logging.warn("Core application using SQLite db file: %s", _config['dbfile'])

_app = Flask(__name__)
_app.config['SQLALCHEMY_DATABASE_URI'] = db_connection_string
db = SQLAlchemy(_app)

db.create_all()
