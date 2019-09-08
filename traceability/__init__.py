"""
The PLC Python library.
"""
__version__ = '0.11.2'
AUTHOR = "Piotr Wilkosz"
EMAIL = "Piotr.Wilkosz@gmail.com"
NAME = "ProdLineTrace"

import logging
import tempfile
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .helpers import parse_config, parse_args

logger = logging.getLogger(__package__.ljust(12)[:12])

_opts, _args = parse_args()
_config = {}

try:
    _config['dburi'] = parse_config(_opts.config)['main']['dburi'][0]
except Exception, e:
    _config['dburi'] = 'sqlite:///' + tempfile.gettempdir() + os.sep + NAME + '.sqlite'
    
if 'DATABASE_URL' in os.environ: 
    _config['dburi'] = os.environ.get('DATABASE_URL')

_app = Flask(__name__)
_app.config['SQLALCHEMY_DATABASE_URI'] = _config['dburi']
_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(_app)

# try to create schema
from models import User, Comment, Product, Station, Status, Operation, Operation_Status, Operation_Type, Unit, Variant
db.create_all()
db.session.commit()