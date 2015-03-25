import sys
from plc.PLCPartner import PLCPartner
import plc.util


remoteIP = '192.168.0.1'
remoteTSAP = 2
remoteRack = 0
remoteSlot = 2
ownIP = '192.168.0.2'
ownTSAP = 1000
remoteTSAP = 1002
connectionTimeout = 10
# print " value %d " % 0x1000


def test():
    print "This is a test that connects to partner and waits for message."
    print "Once it gets message it prints it and sends it back to plc."

    plc1 = PLCPartner(ownIP, remoteIP, ownTSAP, remoteTSAP, False)
    plc1.connect()
    partner = plc1.getPartner()
    while True:
        print "waiting for message"
        msg = partner.b_recv()
        print "Message recieved, dumping message"
        plc.util.hexdump(msg)
        partner.b_send(msg)
        print "Message sent back to partner"
        print "times: ", partner.get_times()
        break
    plc1.disconnect()
    print "disconnected. exit."

sys.exit(test())
