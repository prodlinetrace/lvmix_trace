#!/usr/bin/env
import logging
import os
from plc import controller

c = controller.Controller('192.168.0.10')
logging.root.setLevel(logging.INFO)
logging.info("Connecting controller: %s " % c.getName())
c.connect()
logging.info("Controller name: %s status: %s " % (c.getName(), c.getStatus()))

for db in [300, 301, 302, 303, 310]:
    data = c.getDb(db)
    f = os.path.join(os.path.dirname(os.path.abspath(os.path.curdir)), 'data', 'dbdump', str(db) + '.db')
    logging.info("saving data item %s to %s file" % (db, f))
    open(f, "wb").write(data)
c.disconnect()
