#!/usr/bin/python
from plc import db
from datetime import datetime
import hashlib
from markdown import markdown
import bleach
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import request, current_app
from flask.ext.login import UserMixin
import logging
__version__ = '0.1.1'

logger = logging.getLogger(__name__)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), nullable=False, unique=True, index=True)
    is_admin = db.Column(db.Boolean)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    locale = db.Column(db.String(16))
    bio = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    comments = db.relationship('Comment', lazy='dynamic', backref='author')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.login is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.login.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        _hash = self.avatar_hash or hashlib.md5(self.login.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=_hash, size=size, default=default, rating=rating)

    def get_api_token(self, expiration=300):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'user': self.id}).decode('utf-8')

    @staticmethod
    def validate_api_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        _id = data.get('user')
        if _id:
            return User.query.get(_id)
        return None


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)  # this is serial number
    type = db.Column(db.Integer, index=True, unique=False)
    serial = db.Column(db.Integer, index=True, unique=False)
    week = db.Column(db.Integer, unique=False)
    year = db.Column(db.Integer, unique=False)
    date_added = db.Column(db.DateTime(), index=True, default=datetime.utcnow)
    comments = db.relationship('Comment', lazy='dynamic', backref='product')
    statuses = db.relationship('Status', lazy='dynamic', backref='product')
    operations = db.relationship('Operation', lazy='dynamic', backref='product')

    def __init__(self, type, serial, week, year):
        self.type = type
        self.serial = serial
        self.week = week
        self.year = year
        self.id = self.get_product_id(self.type, self.serial)

    def __repr__(self):
        return '<Product %d>' % self.id

    def get_product_id(self, type=None, serial=None):
        """
        returns product id based on product_type and serial_number.
        It is used within Product table.
        """
        if type is None:
            type = self.type

        if serial is None:
            serial = self.serial
            
        return pow(10, 8) * type + serial

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'type': self.type,
            'serial': self.serial,
            'week': self.week,
            'year': self.year,
        }


class Station(db.Model):
    __tablename__ = 'station'
    id = db.Column(db.Integer, primary_key=True)  # this is real station id
    ip = db.Column(db.String(16), unique=False)
    name = db.Column(db.String(64), unique=False)
    port = db.Column(db.Integer, unique=False)
    rack = db.Column(db.Integer, unique=False)
    slot = db.Column(db.Integer, unique=False)
    statuses = db.relationship('Status', lazy='dynamic', backref='station')
    operations = db.relationship('Operation', lazy='dynamic', backref='station')

    def __init__(self, _id, _ip='localhost', _name="name", _port=102, _rack=0, _slot=2):
        self.id = _id
        self.ip = _ip
        self.name = _name
        self.port = _port
        self.rack = _rack
        self.slot = _slot

    def __repr__(self):
        return '<Station %r>' % self.id

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'port': self.port,
            'rack': self.rack,
            'slot': self.slot,
        }


class Status(db.Model):
    __tablename__ = 'status'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer)
    date_time = db.Column(db.String(40))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'))

    def __init__(self, _status, _product, _station, _date_time=None):
        self.status = _status
        self.product_id = _product
        self.station_id = _station
        if _date_time is None:
            _date_time = datetime.now()
        self.date_time = str(_date_time)

    def __repr__(self):
        return '<Status Product: %d Station: %r Status: %r>' % (self.product_id, self.station_id, self.status)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'status': self.status,
            'product_id': self.product_id,
            'station_id': self.station_id,
            'date_time': self.date_time,
        }


class Operation(db.Model):
    __tablename__ = 'operation'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'))
    operation_status = db.Column(db.Integer)
    operation_type_id = db.Column(db.Integer, db.ForeignKey('operation_type.id'))
    date_time = db.Column(db.String(40))
    result_1 = db.Column(db.Float)
    result_1_max = db.Column(db.Float)
    result_1_min = db.Column(db.Float)
    result_1_status = db.Column(db.Float)
    result_2 = db.Column(db.Float)
    result_2_max = db.Column(db.Float)
    result_2_min = db.Column(db.Float)
    result_2_status = db.Column(db.Float)
    result_3 = db.Column(db.Float)
    result_3_max = db.Column(db.Float)
    result_3_min = db.Column(db.Float)
    result_3_status = db.Column(db.Float)

    def __init__(self, _product, _station, _operation_status, _operation_type_id, _date_time, _r1=None, _r1_min=None, _r1_max=None, _r1_stat=None, _r2=None, _r2_min=None, _r2_max=None, _r2_stat=None, _r3=None, _r3_min=None, _r3_max=None, _r3_stat=None):
        self.product_id = _product
        self.station_id = _station
        self.operation_status = _operation_status
        self.operation_type_id = _operation_type_id
        if _date_time is None:
            _date_time = datetime.now()
        self.date_time = str(_date_time)

        self.result_1 = _r1
        self.result_1_max = _r1_max
        self.result_1_min = _r1_min
        self.result_1_status = _r1_stat

        self.result_2 = _r2
        self.result_2_max = _r2_max
        self.result_2_min = _r2_min
        self.result_2_status = _r2_stat

        self.result_3 = _r3
        self.result_3_max = _r3_max
        self.result_3_min = _r3_min
        self.result_3_status = _r3_stat

    def __repr__(self):
        return '<Assembly Operation for: Product: %r Station: %r Operation_type: %r>' % (self.product_id, self.station_id, self.operation_type_id)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""

        return {
            'id': self.id,
            'product_id': self.product_id,
            'station_id': self.station_id,
            'operation_type_id': self.operation_type_id,
            'operation_status': self.operation_status,
            'date_time': self.date_time,

            'result_1': self.result_1,
            'result_1_max': self.result_1_max,
            'result_1_min': self.result_1_min,
            'result_1_status': self.result_1_status,

            'result_2': self.result_2,
            'result_2_max': self.result_2_max,
            'result_2_min': self.result_2_min,
            'result_2_status': self.result_2_status,

            'result_3': self.result_3,
            'result_3_max': self.result_3_max,
            'result_3_min': self.result_3_min,
            'result_3_status': self.result_3_status,
        }


class Operation_Type(db.Model):
    __tablename__ = 'operation_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(255))
    operations = db.relationship('Operation', lazy='dynamic', backref='operation_type')

    def __init__(self, _id, _name="Default Operation Name", _description="Default Operation Description"):
        self.id = _id
        self.name = _name
        self.description = _description

    def __repr__(self):
        return '<Operation_Type Id: %r Name: %r Description: %r>' % (self.id, self.name, self.description)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }
