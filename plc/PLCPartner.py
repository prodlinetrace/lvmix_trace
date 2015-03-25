from snap7.partner import Partner
import time
import logging
logger = logging
# logger.addHandler(hdlr)

"""
This class creates single PLC partner connection.
Implements correct logging functionality and some other extras.
"""


class PLCPartner():
    def __init__(self, ownIP, remoteIP, ownTSAP, remoteTSAP, active=False, timeout=10, reconnect=3):
        self.ownIP = ownIP
        self.remoteIP = remoteIP
        self.ownTSAP = ownTSAP
        self.remoteTSAP = remoteTSAP
        self.active = active
        self.connectionTimeout = timeout  # partner connection timeout in seconds
        self.reconnect = reconnect  # number of attempts to reconnect
        self.connectionStatusCodes = {
            0: {"func": "par_stopped", "desc": "Stopped."},
            1: {"func": "par_connecting", "desc": "Running, active and trying to connect."},
            2: {"func": "par_waiting", "desc": "Running, passive and waiting for a connection"},
            3: {"func": "par_connected", "desc": "Connected."},
            4: {"func": "par_sending", "desc": "Sending data."},
            5: {"func": "par_receibing", "desc": "Receiving data."},
            6: {"func": "par_binderror", "desc": "Error starting passive partner."},
        }

    def connect(self, attempt=0):
        if attempt < self.reconnect:
            attempt += 1  # increment connection attempts
            logger.warning("Trying to connect to partner: %s %s" % (self.remoteIP, self.remoteTSAP))
            logger.warning("attempt: %s/%s (timeout: %s seconds)" % (attempt, self.reconnect, self.connectionTimeout))
            self.partner = Partner(self.active)
            self.partner.start_to(self.ownIP, self.remoteIP, self.ownTSAP, self.remoteTSAP)
            t = 0
            while t < self.connectionTimeout:
                if self.partner.get_status().value == 3:
                    break
                time.sleep(1)
                t += 1

            if self.partner.get_status().value == 3:
                logger.warn("connected to parent: IP %s TSAP %s" % (self.remoteIP, self.remoteTSAP))
            else:
                self.connect(attempt)
                logger.error("Connection to parent: IP %s TSAP %s Failed" % (self.remoteIP, self.remoteTSAP))
#                print "Status: %s " % self.connectionStatusCodes[self.partner.get_status().value]['desc']
                msg = "Unable connect to IP %s TSAP %s for %s times with timeout %s. Connection status: " % (self.remoteIP, self.remoteTSAP, self.reconnect, self.connectionTimeout) + self.connectionStatusCodes[self.partner.get_status().value]['desc']
                raise(Exception(msg))

    def disconnect(self):
        self.partner.stop()
        self.partner.destroy()

    def setTimeout(self, timeout):
        self.timeout = timeout

    def getTimeout(self):
        return self.timeout

    def getPartner(self):
        return self.partner

    def sync_time(self):
        pass
