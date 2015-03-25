#!flask/bin/python
from flask import Flask
from flask.views import MethodView
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
from plc.constants import STATION_STATUS_CODES
from snap7 import six

from flask import Flask, jsonify, abort, request, make_response, url_for
import flask


import logging
logger = logging.getLogger(__name__)

rest = Flask(__name__, static_url_path="")
rest.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prodLine.db'
db = SQLAlchemy(rest)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # this is serial number
    type = db.Column(db.String(12), unique=False)
    week = db.Column(db.String(4), unique=False)
    year = db.Column(db.String(4), unique=False)

    def __init__(self, _id, _type, _week, _year):
        self.id = _id
        self.type = _type
        self.week = _week
        self.year = _year

    def __repr__(self):
        return '<Item %s>' % str(self.id)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'id': self.id,
           'type': self.type,
           'week': self.week,
           'year': self.year,
        }


class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # this is real station id
    ip = db.Column(db.String(15), unique=False)
    port = db.Column(db.Integer, unique=False)
    rack = db.Column(db.Integer, unique=False)
    slot = db.Column(db.Integer, unique=False)

    def __init__(self, _id, _ip='localhost', _port=102, _rack=0, _slot=2):
        self.id = _id
        self.ip = _ip
        self.port = _port
        self.rack = _rack
        self.slot = _slot

    def __repr__(self):
        return '<Station %s>' % str(self.id)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'id': self.id,
           'ip': self.ip,
           'port': self.port,
           'rack': self.rack,
           'slot': self.slot,
        }


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer)
    date_time = db.Column(db.DateTime)

    item_id = db.Column(db.Integer)
    station_id = db.Column(db.Integer)
    # TODO: make FK relation
    # item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    # item = db.relationship('Item', backref=db.backref('statuses', lazy='dynamic'))
    # station_id = db.Column(db.Integer, db.ForeignKey('station.id'))
    # station = db.relationship('Station', backref=db.backref('statuses', lazy='dynamic'))

    def __init__(self, _status, _item, _station, _date_time=None):
        self.status = _status
        if _date_time is None:
            _date_time = datetime.now()
        self.date_time = _date_time
        self.item_id = _item
        self.station_id = _station

    def __repr__(self):
        return '<Status Item: %s Station: %s Status: %s>' % (self.item_id, self.station_id, self.status)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'id': self.id,
           'status': self.status,
           'item_id': self.item_id,
           'station_id': self.station_id,
           'date_time': self.date_time,
        }


db.drop_all()
db.create_all()

i1 = Item(16666, "666", "42", "15")
i2 = Item(26666, "666", "42", "15")
i3 = Item(1234, "666", "42", "15")
s10 = Station(10, "192.168.0.10", 102, 0, 2)
s20 = Station(20, "192.168.0.20", 102, 0, 2)
s21 = Station(21, "192.168.0.20", 102, 0, 2)
s22 = Station(22, "192.168.0.20", 102, 0, 2)
s23 = Station(23, "192.168.0.20", 102, 0, 2)
t1 = Status(0, 16666, 10, None)
t2 = Status(1, 26666, 20, None)
t3 = Status(0, 1234, 10, None)
t4 = Status(1, 1234, 20, None)

db.session.add(i1)
db.session.add(i2)
db.session.add(i3)

db.session.add(s10)
db.session.add(s20)
db.session.add(s21)
db.session.add(s22)
db.session.add(s23)

db.session.add(t1)
db.session.add(t2)
db.session.add(t3)
db.session.add(t4)

db.session.commit()


@rest.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@rest.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@rest.route("/items", methods=['GET'])
def get_items():
    return jsonify(json_list=[i.serialize for i in Item.query.all()])

@rest.route('/item/<int:id>', methods=['GET'])
def get_item(id):
    item = Item.query.filter_by(id=int(id)).first()
    if item is None:
        abort(404)
    return jsonify({'item': item.serialize})

@rest.route("/items", methods=['POST'])
def create_item():
    if not request.json or "id" not in request.json:
        abort(400)

    new_item = Item(
        int(request.json['id']),
        request.json['type'],
        request.json['week'],
        request.json['year'],
        )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'item': new_item.serialize}), 201
    # TODO: make better request validation like in update_item


# method not allowed see: http://flask-restless.readthedocs.org/en/latest/customizing.html
@rest.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.filter_by(id=int(id)).first()
    if item is None:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'result': True})


# method not allowed see: http://flask-restless.readthedocs.org/en/latest/customizing.html
@rest.route('/items/<int:id>', methods=['PUT'])
def update_item(id):
    item = Item.query.filter_by(id=int(id)).first()
    if item is None:
        abort(404)
    if not request.json:
        abort(400)
    if 'type' in request.json and \
            not isinstance(request.json['type'], six.string_types):
        abort(400)
    if 'week' in request.json and \
            not isinstance(request.json['week'], six.string_types):
        abort(400)
    if 'year' in request.json and \
            not isinstance(request.json['year'], six.string_types):
        abort(400)
    item.type = request.json['type']
    item.week = request.json['week']
    item.year = request.json['year']
    db.session.commit()
    return jsonify({'item': item.serialize})




@rest.route("/stations", methods=['GET'])
def get_stations():
    return jsonify(json_list=[s.serialize for s in Station.query.all()])

@rest.route('/station/<int:id>', methods=['GET'])
def get_station(id):
    station = Station.query.filter_by(id=int(id)).first()
    if station is None:
        abort(404)
    return jsonify({'station': station.serialize})

@rest.route("/stations", methods=['POST'])
def create_station():
    if not request.json or "id" not in request.json:
        abort(400)

    new_station = Station(
        int(request.json['id']),
        request.json['ip'],
        int(request.json['port']),
        int(request.json['rack']),
        int(request.json['slot']),
        )
    db.session.add(new_station)
    db.session.commit()
    return jsonify({'station': new_station.serialize}), 201
    # TODO: make better request validation like in update_item


# TODO add delete and update station

@rest.route("/status", methods=['GET'])
def get_statuses():
    return jsonify(json_list=[i.serialize for i in Status.query.all()])

@rest.route('/status/<int:id>', methods=['GET'])
def get_status(id):
    status = Status.query.filter_by(id=int(id)).first()
    if status is None:
        abort(404)
    return jsonify({'status': status.serialize})

@rest.route('/status/item/<int:item_id>', methods=['GET'])
def get_status_item(item_id):
    statuses = Status.query.filter_by(item_id=int(item_id)).all()
    if statuses is None:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(item_id=int(item_id)).all()])

@rest.route('/status/station/<int:station_id>', methods=['GET'])
def get_status_station(station_id):
    statuses = Status.query.filter_by(station_id=int(station_id)).all()
    if statuses is None:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(station_id=int(station_id)).all()])

@rest.route('/status/station/<int:station_id>/item/<int:item_id>', methods=['GET'])
def get_status_station_item(station_id, item_id):
    statuses = Status.query.filter_by(station_id=int(station_id)).filter_by(item_id=int(item_id)).all()
    if statuses is None:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(station_id=int(station_id)).filter_by(item_id=int(item_id)).all()])

@rest.route('/status/item/<int:item_id>/station/<int:station_id>', methods=['GET'])
def get_status_item_station(station_id, item_id):
    statuses = Status.query.filter_by(station_id=int(station_id)).filter_by(item_id=int(item_id)).all()
    if statuses is None:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(station_id=int(station_id)).filter_by(item_id=int(item_id)).all()])

@rest.route("/status", methods=['POST'])
def create_status():
    if not request.json:
        abort(400)
    if 'status' in request.json and \
            not isinstance(request.json['status'], six.integer_types):
        abort(400)
    if 'item_id' in request.json and \
            not isinstance(request.json['item_id'], six.integer_types):
        abort(400)
    if 'station_id' in request.json and \
            not isinstance(request.json['station_id'], six.integer_types):
        abort(400)
    #if 'date_time' not in request.json:
    #    abort(400)

    new_status = Status(
        request.json['status'],
        request.json['item_id'],
        request.json['station_id']
        #request.json['date_time'],
        )

    db.session.add(new_status)
    db.session.commit()
    return jsonify({'status': new_status.serialize}), 201


@rest.route("/status")
def statuses():
    ret = ''
    for status in Status.query.all():
        s = "id: %s status: %s item: %s station: %s" % (status.id, status.status, status.item_id, status.station_id)
        ret = ret + s + "<br>"
    return ret


@rest.route('/')
def index():
    head = "Welcome to ProdLineTrace RestAPI<br/>"
    tail = """
    Please contact: piotr.wilkosz@gmail.com in case of any questions.
    Enjoy!
    """
    message = """

    --- ITEMS ---
    - Item read
        To list available items please run GET on : http://localhost:5000/items
        To get item with id 2666 please run GET on: http://localhost:5000/item/2666
    - Item write
        To add item please run POST on: http://localhost:5000/items 
            Content Type: application/json 
            Content:
            {
                "id": 2,
                "type": "777",
                "week": "7",
                "year": "7"
            }
    - Item remove
        To delete item with id 2666 please run DELETE on: http://localhost:5000/item/2666
    - Item update
        To update item with id 2666 please run PUT on: http://localhost:5000/item/2666
        Content Type: application/json 
        Content:
        {
            "type": "1",
            "week": "2",
            "year": "3"
        }
    DELETE and PUT are not enabled for time being for security reasons


    --- STATIONS ---
    - Station read:
        To list available stations please run GET on : http://localhost:5000/stations
        To get station with id 20 please run GET on : http://localhost:5000/station/20

    - Station write:
        To add station please run POST on: http://localhost:5000/stations 
            Content Type: application/json with following example 
            Content:
            {
              "id": 10, 
              "ip": "192.168.0.10", 
              "port": 102, 
              "rack": 0,
              "slot": 2,  
            }
    - Station remove
        To delete station with id 20 please run DELETE on: http://localhost:5000/station/20
    - Station update
        To update station with id 20 please run PUT on: http://localhost:5000/station/20
        Content Type: application/json 
        Content:
        {
            "type": "1",
            "week": "2",
            "year": "3"
        }
    DELETE and PUT are not enabled for time being for security reasons
    # TODO stations update and remove (PUT and DELETE)


    --- STATUSES ---
    - Status read:
        - to get the list of all statuses please run GET on
        http://localhost:5000/status
        - to get the status with id 1 please run GET on
        http://localhost:5000/status/1
        - to get the list of statuses on all stations for item with id 1234 please run GET on
        http://localhost:5000/status/item/1234
        - to get the list of all statuses on station with id 20 run GET on
        http://localhost:5000/status/station/20
        - to get the list of statuses on station 20 for item with id 1234 run GET on either of URLs 
        http://localhost:5000/status/station/20/item/1234
        http://localhost:5000/status/item/1234/station/20

    - Status write 
        - to write status for given item and station please run POST on:
        http://localhost:5000/status
            with following example content:
            Content Type: application/json  
            Content:
            {
                "status": 
                "item_id": 16666, 
                "station_id": 10, 
                "date_time": "Thu, 05 Feb 2015 03:53:01 GMT", 
            }

    - Status remove
        To delete status with id 1 please run DELETE on: http://localhost:5000/status/1

    # TODO status UPDATE and REMOVE

    --- STATUS CODES ---
    Please find meaning of available status codes:
    %s

    """ % (str(STATION_STATUS_CODES))
    return "\n".join([head, message, tail]).replace("\n", "<br/>\n")

rest.run(debug=True)