import snap7
import sys

remoteIP = '192.168.0.1'
remoteTSAP = 2
remoteRack = 0
remoteSlot = 2
ownIP = '192.168.0.2'
ownTSAP = 1000
remoteTSAP = 1002
connectionTimeout = 10


def clientTest():
    print "This is a test that connects to client and list available blocks."

    c = snap7.client.Client()
    c.connect(remoteIP, remoteRack, remoteSlot)
    # c.as_db_write(db_number, start, data)
    # c.connect(remoteIP)
    print "client connect: OK"
    print c.list_blocks()
    # print c.list_blocks_of_type("DB", 7)
    # print c.
    c.disconnect()

sys.exit(clientTest())
