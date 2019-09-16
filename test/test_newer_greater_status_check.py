#!/usr/bin/env python
import os
import time
import datetime
import logging
import sys

logging.root.setLevel(logging.DEBUG)

from traceability import plc


p = plc.PLC()
print (p)

assert p.get_newer_greater_status_check() is True, "get newer_greater_status_check value (default)"
p.set_newer_greater_status_check(False) 
assert p.get_newer_greater_status_check() is False, "set newer_greater_status_check value"
p.set_newer_greater_status_check(True)
db_uri=' mysql+pymysql://trace:trace@localhost/trace'
p._init_database(db_uri)
#print p.database_engine

product_id="46400601205131043619"
station_number=14

print p.database_engine.read_status(product_id, station_number)
                              
assert p.database_engine.read_status(product_id, station_number) == 1, "Read the status from product_id: {product_id} station: {station_number}".format(station_number=station_number, product_id=product_id)
print p.database_engine.newer_greater_status(str(product_id), int(station_number))


#p.newer_greater_status(self, product_id, station)
#p.newer_greater_status(self, product_id, station):

