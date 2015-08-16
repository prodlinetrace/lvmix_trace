#!/usr/bin/env
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.curdir)))
from plc import controller

c = controller.Controller('192.168.0.20')
logging.root.setLevel(logging.INFO)
logging.info("Connecting controller: %r " % c)
c.connect()
c.set_id('c2')
logging.info("Controller name: %s status: %s " % (c.get_name(), c.get_status()))

for db in [300, 301, 302, 303, 304]:
    _db = c.get_db(db)
    _bytearray = _db.get_bytearray()

    f = os.path.join(os.path.dirname(os.path.abspath(os.path.curdir)), 'data', 'dbdump', str(db) + '.db')
    logging.info("saving data item %s to %s file" % (db, f))
    open(f, "wb").write(_bytearray)
c.disconnect()
