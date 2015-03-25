# this is a class of PLC controller Simulator
import snap7
import logging
from plc.datablocks import DataBlocks
from plc.controller import ControllerBase
from plc.custom_exceptions import UnknownStation, UnknownDb, UnknownSN
import time
from plc.custom_exceptions import PLCSendRcvTimeOut
from plc.constants import STATION_STATUS, SERIAL_NUMBER, STATION_NUMBER, STATION_STATUS_CODES
import random

logger = logging.getLogger(__name__)


class Simulator(ControllerBase):
    """
    Simulator is two in one Server and CLient.
    """

    def __init__(self, ip='127.0.0.1', rack=0, slot=2, port=102, reconnect=3):
        ControllerBase.__init__(self, ip, rack, slot, port, reconnect)
        self.__ip = ip
        self.__rack = int(rack)
        self.__slot = int(slot)
        self.__port = int(port)
        self.__name = self.__ip
        self.__id = self.__ip
        self.server = snap7.server.Server()
        self.serial_numbers = ['123', '4321123', '6666666', '1234432', '8765432']
        self.serial_numbers = [u'12345678\n']
        self.station_numbers = [11, 12, 13, 21, 22, 23, 31, 32, 33]
        self.assembly_statuses = [0, 1, 2]

    def connect(self, attempt=0):
        self.server.start_to(self.__ip, self.__port)
        # self.client.connect(self.__ip, self.__rack, self.__slot, self.__port)
        ControllerBase.connect(self, attempt)

    def disconnect(self):
        if self.database_engine is not None:
            self.database_engine.disconnect()
        self.client.disconnect()
        self.client.destroy()
        self.server.destroy()

    def get_server(self):
        return self.server

    def register_area(self, area_code, index, data):
        type_ = snap7.snap7types.wordlen_to_ctypes[snap7.snap7types.S7WLByte]
        size = len(data)
        cdata = (type_ * size).from_buffer(data)
        self.get_server().register_area(area_code, index, cdata)

    def save_station_status(self, dbid=None, serial_number=None, station=None, status=None):
        # raise NotImplementedError('Please implement this method on %s' % self.__class__.__name__)
        if station is None:
            raise UnknownStation(station)

        if serial_number is None:
            raise UnknownSN(station)

        if dbid is None:
            raise UnknownDb(dbid)

        logger.info("PLC: %s DB: %s SN: %s ST: %s saving assembly information." % (self.get_id(), dbid, serial_number, station))
        db = self.get_db(dbid)

        # wait for PC_READY_FLAG to start processing 
        logger.debug("PLC: %s DB: %s SN: %s ST: %s waiting for PC_READY_FLAG" % (self.get_id(), dbid, serial_number, station))
        i = 0
        while i < 30:
            i += 1
            if db.pc_ready_flag() == True:
                break
            time.sleep(0.1)
        print "I:", i
        if i == 30:
            logger.warning("PLC: %s DB: %s SN: %s ST: %s Timeout getting PC_READY flag" % (self.get_id(), dbid, serial_number, station)) 
            return False # timeout
        logger.debug("PLC: %s DB: %s SN: %s ST: %s got PC_READY_FLAG" % (self.get_id(), dbid, serial_number, station))

        # write serial number to PLC memory before  
        db.store_item(SERIAL_NUMBER, serial_number)
        # write station number to PLC memory
        db.store_item(STATION_NUMBER, station)
        # write status to PLC memory
        db.store_item(STATION_STATUS, status)

        db.set_plc_save_flag(True)  # set message flag - wait for PC to process it!
        time.sleep(0.5) # wait to save.
        # wait for response # check if PLC_SAVE_FLAG was cancelled by application
        logger.debug("PLC: %s DB: %s SN: %s ST: %s waiting for PLC_SAVE_FLAG" % (self.get_id(), dbid, serial_number, station))
        i = 0
        while i < 30:
            i += 1
            if db.plc_save_flag() == False:
                break
            time.sleep(0.1)
        if i == 30:
            logger.warning("PLC: %s DB: %s SN: %s ST: %s Timeout getting PLC_SAVE_FLAG flag" % (self.get_id(), dbid, serial_number, station)) 
            return False # timeout
        #print "CAN SAVE NOW"
        logger.debug("PLC: %s DB: %s SN: %s ST: %s got PLC_SAVE_FLAG" % (self.get_id(), dbid, serial_number, station))

        # get the status description
        # status = STATION_STATUS_CODES[_status]['result']
        logger.info("PLC: %s DB: %s SN: %s ST: %s assembly status saved and is: %s" % (self.get_id(), dbid, serial_number, station, status))
        # reset plc_message flag - should be done already by PC anyway
        db.set_plc_save_flag(False)
        return status

    def get_station_status(self, dbid, serial_number, station=None):
        # raise NotImplementedError('Please implement this method on %s' % self.__class__.__name__)
        if dbid is None:
            raise UnknownDb(dbid)

        if serial_number is None:
            raise UnknownSN(station)

        if station is None:
            raise UnknownStation(station)

        logger.info("PLC: %s DB: %s SN: %s reading assembly from station : %s" % (self.get_id(), dbid, serial_number, station))
        db = self.get_db(dbid)

        # wait for PC_READY_FLAG to start processing
        logger.debug("PLC: %s DB: %s SN: %s ST: %s waiting for PC_READY_FLAG" % (self.get_id(), dbid, serial_number, station))
        i = 0
        while i < 30:
            i += 1
            if db.pc_ready_flag() == True:
                break
            time.sleep(0.1)
        print "I:", i
        if i == 30:
            logger.warning("PLC: %s DB: %s SN: %s ST: %s Timeout getting PC_READY flag" % (self.get_id(), dbid, serial_number, station)) 
            return False # timeout
        logger.debug("PLC: %s DB: %s SN: %s ST: %s got PC_READY_FLAG" % (self.get_id(), dbid, serial_number, station))

        # write serial number to PLC memory before
        #print "Storing: ", serial_number, "xx"
        db.store_item(SERIAL_NUMBER, serial_number)

        db.store_item(STATION_STATUS, 9)  # reset station status to "waiting state"
        db.set_plc_message_flag(True)  # set message flag

        # wait for response # check if PLC_SAVE_FLAG was cancelled by application
        logger.debug("PLC: %s DB: %s SN: %s ST: %s waiting for PLC_MESSAGE_FLAG" % (self.get_id(), dbid, serial_number, station))
        i = 0
        while i < 30:
            i += 1
            if db.plc_message_flag() == False:
                break
            time.sleep(0.1)
        if i == 30:
            logger.warning("PLC: %s DB: %s SN: %s ST: %s Timeout getting PLC_MESSAGE_FLAG flag" % (self.get_id(), dbid, serial_number, station)) 
            return False # timeout
        logger.debug("PLC: %s DB: %s SN: %s ST: %s got PLC_MESSAGE_FLAG" % (self.get_id(), dbid, serial_number, station))

        """
        # wait for response # check if station status has changed.
        # TODO: check if this is the right indicator.
        while True:
            if db.read_item(STATION_STATUS) != 9:
                break
            time.sleep(0.1)
        _status = db.read_item(STATION_STATUS)
        """

        _status = db.read_item(STATION_STATUS)
        # get the status description
        status = STATION_STATUS_CODES[_status]['result']
        logger.info("PLC: %s DB: %s SN: %s ST: %s assembly status is: %s" % (self.get_id(), dbid, serial_number, station, status))
        # reset plc_message flag
        db.set_plc_message_flag(False)
        return status

    def run(self):
        for dbid in self.get_active_dbs():
            print dbid, "read"
            self.read_test(dbid)
            print dbid, "save"
            self.save_test(dbid)

    def save_test(self, dbid):
        serial = random.choice(self.serial_numbers)
        station = random.choice(self.station_numbers)
        status = random.choice(self.assembly_statuses)
        logger.info("Simulator: %s DB: %s SN: %s ST: %s Saving status %s" % (self.get_id(), dbid, serial, station, status))
        self.save_station_status(dbid, serial, station, status)

    def read_test(self, dbid):
        serial = random.choice(self.serial_numbers)
        station = random.choice(self.station_numbers)
        logger.info("Simulator: %s DB: %s SN: %s ST: %s Reading status" % (self.get_id(), dbid, serial, station))
        self.get_station_status(dbid, serial, station)
