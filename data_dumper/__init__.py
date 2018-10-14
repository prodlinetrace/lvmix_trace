from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(uri='sqlite:///data-dev.sqlite'):
    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = uri  
    db.init_app(app)
    
    return app

app = create_app('sqlite:///prodLineTrace.db')
db = SQLAlchemy(app)
from models import *
db.create_all()