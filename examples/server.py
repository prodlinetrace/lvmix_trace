import snap7
import os
import sys
import logging
from time import sleep
logging.root.setLevel(logging.INFO)

ip = '0.0.0.0'
port = 2102

def register_area(server, area_code, index, data):
    _type = snap7.snap7types.wordlen_to_ctypes[snap7.snap7types.S7WLByte]
    size = len(data)
    cdata = (_type * size).from_buffer(data)
    server.register_area(area_code, index, cdata)


server = snap7.server.Server()
server.create()
logging.info("creating server on: {ip}:{port}".format(ip=ip, port=port))


for db in [300, 301, 302, 303, 304]:
    dbAreaCode = snap7.snap7types.srvAreaDB
    f = os.path.join(os.path.dirname(os.path.abspath(os.path.curdir)), 'data', 'dbdump', str(db) + '.db')
    data = bytearray(open(f, "rb").read())
    register_area(server, dbAreaCode, db, data)
    #logging.info("Registered db: %s" % (db))

server.start_to(ip, port)

while(True):
    sleep(1)