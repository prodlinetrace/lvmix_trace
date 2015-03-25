# this is a class of PLC controller
import snap7
import logging
from constants import *
from plc.util import get_product_id
from plc.datablocks import DataBlocks
from plc.custom_exceptions import UnknownDb
from plc.database import Database
from datetime import datetime
from time import sleep

logger = logging.getLogger(__name__)


class ControllerBase(object):

    def __init__(self, ip='127.0.0.1', rack=0, slot=2, port=102, reconnect=3):
        self.__ip = ip
        self.__rack = int(rack)
        self.__slot = int(slot)
        self.__port = int(port)
        self.client = snap7.client.Client()
        self.__name = self.__ip
        self.__id = self.__ip
        self._reconnect = reconnect  # number of attempts to reconnect
        self.time = None
        self._active_data_blocks = []
        # configure database items
        self.database_engine = None
        self.database_client = None
        self.database_cursor = None
        self.counter_status_message_read = 0
        self.counter_status_message_write = 0
        self.counter_saved_operations = 0

    def _init_database(self, dbfile='data/prodline.db'):
        self.database_engine = Database()
        logger.info("PLC: %s connected to SQLite @ %s. Status: %s" % (self.get_id(), dbfile, self.database_engine.get_status()))

    def __repr__(self):
        return """<%s.%s %s>""" % (self.__class__.__module__, self.__class__.__name__, str(self))

    @property
    def dbs(self):
        return DataBlocks(self)

    @property
    def active_dbs(self):
        # we should list configuration file activated data blocks only
        ret = {}
        for k, v in DataBlocks(self).items():
            if k in self._active_data_blocks:
                ret[k] = v
        return ret

    def items(self):
        """
        :param return: A list of pairs. Each pair will be (db name, db object)
        """
        return list(self.dbs.items())

    def __getitem__(self, dbid):
        """
        Get a db by number
        :param db: number of the db, int
        :return: db obj
        """
        return self.dbs[dbid]
        raise UnknownDb("failed to get db: %s" % dbid)

    def iteritems(self):
        """
        Get the names & objects for all db's
        """
        return self.dbs.iteritems()

    def __contains__(self, dbid):
        """
        True if db is the number of a defined Data Block
        """
        return dbid in self.keys()

    def get_dbs(self):
        return self.items()

    def get_active_dbs(self):
        return self.active_dbs

    def get_db(self, dbid):
        """
        Get a db by number
        :param db: number of the db, int
        :return: db obj
        """
        return self.dbs[dbid]

    def keys(self):
        return [a for a in self.iterkeys()]

    def iterkeys(self):
        for block in self.dbs.iterkeys():
            yield block

    def __str__(self):
        return "PLC Controller Id: %s Name: %s @ %s:%s" % (self.__id, self.__name, self.__ip, self.__port)

    def connect(self, attempt=0):
        if attempt < self._reconnect:
            attempt += 1  # increment connection attempts
            logger.debug("PLC: %s Trying to connect to server: %s %s %s %s. Attempt: %s/%s" % (self.__id, self.__ip, self.__rack, self.__slot, self.__port, attempt, self._reconnect))
            try:
                self.client.connect(self.__ip, self.__rack, self.__slot, self.__port)
            except snap7.snap7exceptions.Snap7Exception:
                logger.warning("PLC: %s connection to server: IP %s PORT %s Failed attempt %s/%s" % (self.__id, self.__ip, self.__port, attempt, self._reconnect))
                self.client.disconnect()
                sleep(1)

            if self.client.get_connected():
                logger.info("PLC: %s connected to server: IP %s PORT %s" % (self.__id, self.__ip, self.__port))
            else:
                logger.error("PLC: %s connection to server: IP %s PORT %s Failed attempt %s/%s" % (self.__id, self.__ip, self.__port, attempt, self._reconnect))
                self.connect(attempt)
                return

    def disconnect(self):
        logger.debug("PLC: %s. disconnecting procedure started..." % (self.get_id()))
        self.cancel_pc_busy_flags()
        if self.database_engine is not None:
            self.database_engine.disconnect()
        self.client.disconnect()

    def cancel_pc_busy_flags(self):
        for _dbno in self.get_active_dbs():
            _block = self.get_db(_dbno)
            _block.set_pc_ready_flag(True)

    def get_client(self):
        return self.client

    def get_time(self):
        logger.debug("PLC: %s. Reading time from controller." % (self))
        self.time = self.client.get_plc_date_time()
        return self.time

    def set_time(self, dtime):
        """
            Sets the time on controller. Please use datetime.datetime input value format
        """
        logger.info("PLC: %s. Setting time on controller to: %s." % (self, dtime))
        self.client.set_plc_date_time(dtime)
        self.time = dtime

    def sync_time(self):
        """
            Synchronizes time on the controller with PC.
        """
        logger.info("PLC: %s. Synchronizing controller time with PC" % (self))
        self.client.set_plc_system_date_time()

    def sync_time_if_needed(self, diff=3):
        """
            Synchronizes time on the controller with PC.
            Time sync will be started if time differs more than `diff` value
            :param diff - time diff in seconds that triggers the sync (default 3 seconds)
        """
        ctrl_time = self.get_time()
        delta = datetime.now() - ctrl_time
        if abs(delta.total_seconds()) > diff:
            logger.info("PLC: %s. Time diff between PLC and PC (%d) is bigger than the trigger(%d). Synchronizing." % (self, abs(delta.total_seconds()), diff))
            self.sync_time()

    def blink_pc_heartbeat(self):
        """
            Changes status of PC heart beat flag.
        """
        for dbid in self.get_active_datablock_list():
            _block = self.get_db(dbid)

            if _block is None:
                logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
                return

            if PC_HEARTBEAT_FLAG in _block.export():
                # change the status of PLC_HEARTBEAT_FLAG flag
                if _block.__getitem__(PC_HEARTBEAT_FLAG) is True:
                    _block.set_flag(PC_HEARTBEAT_FLAG, False)
                else:
                    _block.set_flag(PC_HEARTBEAT_FLAG, True)

    def get_name(self):
        return self.__name

    def set_name(self, value):
        self.__name = value

    def get_id(self):
        return self.__id

    def set_id(self, value):
        self.__id = value

    def get_status(self):
        return self.client.get_connected()

    def get_ip(self):
        return self.__ip

    def get_port(self):
        return self.__port

    def set_active_datablock_list(self, dbs):
        self._active_data_blocks = dbs

    def get_active_datablock_list(self):
        return self._active_data_blocks


class Controller(ControllerBase):

    def __init__(self, ip='127.0.0.1', rack=0, slot=2, port=102, reconnect=3):
        ControllerBase.__init__(self, ip, rack, slot, port, reconnect)

    def poll(self):
        for dbid in self.get_active_dbs():
            self.poll_db(dbid)

    def poll_db(self, dbid):
        # print "reading db", db, "from PLC", self.get_id()
        """
        This function will check if there's some message to be processed.
        It will take necessary actions if required.
        1. Remove missing blocks from plc
        2. db300 handling:
        2.1. reset pc_ready to have clean start
        2.2. Read station status from database and respond to status query message.
        2.3. Save station status to database.
        3. Save operations from tracebility template blocks to database.
        """
        # logger.debug("PLC: %s polling db: %s" % (self.get_id(), db))

        # remove block from active list if not found.
        block = self.get_db(dbid)
        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Removing from active block list." % (self.get_id(), dbid))
            self._active_data_blocks.remove(dbid)
            logger.info("PLC: %s Remaining active block list %r" % (self.get_id(), self._active_data_blocks))
            return

        # status exchange on db300 only
        if dbid == 300:
            # reset pc_ready flag in case it get's accidentally changed.
            block.set_pc_ready_flag(True)
            self.read_status(dbid)
            self.save_status(dbid)
        else:
            self.save_operation(dbid)

    def read_status(self, dbid):
        block = self.get_db(dbid)
        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
            return

        if PLC_MESSAGE_FLAG in block.export():
            if block.__getitem__(PLC_MESSAGE_FLAG):  # get the station status from db
                # body.PC_Redy set false
                block.set_pc_ready_flag(False)  # set PC ready flag to False
                # body
                if STATION_NUMBER not in block.export():
                    logger.warning("PLC: %s, block: %s, has no %s, in block body: %s. Message (block) skipped." % (self.get_id(), block.get_db_number(), STATION_NUMBER, block.export()))
                    return
                product_type = block[PRODUCT_TYPE]
                serial_number = block[SERIAL_NUMBER]
                station_number = block[STATION_NUMBER]
                logger.debug("PLC: %s, block: %s, PT %s, SN: %s, reading status from database for station: %s" % (self.get_id(), block.get_db_number(), product_type, serial_number, station_number))

                result = self.database_engine.read_status(int(product_type), int(serial_number), int(station_number))
                _status = result
                status = STATION_STATUS_CODES[_status]['result']
                block.store_item(STATION_STATUS, _status)
                logger.info("PLC: %s, block: %s, PT: %s, SN: %s, ST: %s, status from database: %s (%s)" % (self.get_id(), block.get_db_number(), product_type, serial_number, station_number, _status, status))
                block.set_pc_ready_flag(True)  # set busy flag to ready
                self.counter_status_message_read += 1

                block.set_plc_message_flag(False)

            else:
                pass
                # too verbose
                # logger.debug("PLC: %s block: %s flag '%s' idle" % (self.get_id(), block.get_db_number(), PLC_MESSAGE_FLAG))

    def save_status(self, dbid):
        # save the status to
        block = self.get_db(dbid)
        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
            return

        if PLC_SAVE_FLAG in block.export():
            if block.__getitem__(PLC_SAVE_FLAG):  # get the station status from db
                # body.PC_Redy set false
                block.set_pc_ready_flag(False)  # set PC ready flag to False
                # query controller. for required fields...
                for field in [STATION_NUMBER, STATION_STATUS, SERIAL_NUMBER, PRODUCT_TYPE]:
                    if field not in block.export():
                        logger.warning("PLC: %s, block: %s, is missing field %s, in block body: %s. Message skipped." % (self.get_id(), block.get_db_number(), field, block.export()))
                        return

                try:
                    station_number = int(block[STATION_ID])
                except ValueError:
                    station_number = 0
                try:
                    _status = int(block[STATION_STATUS])
                except ValueError:
                    _status = 0

                try:
                    status = STATION_STATUS_CODES[_status]['result']
                except ValueError:
                    logger.warning("PLC: %s, block: %s wrong value for status, returning undefined" % (self.get_id(), block.get_db_number()))
                    status = STATION_STATUS_CODES[99]['result']

                try:
                    serial_number = int(block[SERIAL_NUMBER])
                except ValueError:
                    serial_number = 0
                    
                try:
                    product_type = int(block[PRODUCT_TYPE])
                except ValueError:
                    product_type = 0

                logger.info("PLC: %s, block: %s, PT: %s, SN: %s, ST: %s, saving status: %s (%s), to database" % (self.get_id(), block.get_db_number(), product_type, serial_number, station_number, _status, status))

                # store additional data:
                try:
                    week_number = int(block['head.week_number'])
                except ValueError:
                    week_number = 0
                try:
                    year_number = int(block['head.year_number'])
                except ValueError:
                    year_number = 0
                try:
                    date_time = str(block['head.date_time'])
                except ValueError:
                    date_time = str(datetime.datetime.now())

                self.database_engine.write_status(product_type, serial_number, station_number, _status, week_number, year_number, date_time)

                block.set_pc_ready_flag(True)  # set PC ready flag
                self.counter_status_message_write += 1

                block.set_plc_save_flag(False)
            else:
                pass
                # too verbose
                # logger.debug("PLC: %s, block: %s, flag %s idle" % (self.get_id(), block.get_db_number(), PLC_SAVE_FLAG))

    def save_operation(self, dbid):
        block = self.get_db(dbid)

        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
            return

        if TRC_TMPL_COUNT in block.export():
            template_count = block.__getitem__(TRC_TMPL_COUNT)
            # query db for basic fields...
            for field in [STATION_ID, SERIAL_NUMBER, PRODUCT_TYPE]:
                if field not in block.export():
                    logger.warning("PLC: %s, block: %s, is missing field %s, in block body: %s. Message skipped." % (self.get_id(), block.get_db_number(), field, block.export()))
                    return
            # get some basic data from the header
            try:
                product_type = int(block[PRODUCT_TYPE])
            except ValueError:
                product_type = 0
            try:
                serial_number = int(block[SERIAL_NUMBER])
            except ValueError:
                serial_number = 0
            try:
                station_number = int(block[STATION_ID])
            except ValueError:
                station_number = 0
            try:
                week_number = int(block['head.week_number'])
            except ValueError:
                week_number = 0
            try:
                year_number = int(block['head.year_number'])
            except ValueError:
                year_number = 0

            for template_number in range(0, template_count):
                pc_save_flag_name = "body.trc.tmpl.__no__.PLC_Save".replace("__no__", str(template_number))
                operation_status_name = "body.trc.tmpl.__no__.operation_status".replace("__no__", str(template_number))
                operation_type_name = "body.trc.tmpl.__no__.operation_type".replace("__no__", str(template_number))
                date_time_name = "body.trc.tmpl.__no__.date_time".replace("__no__", str(template_number))

                result_1_name = "body.trc.tmpl.__no__.1.result".replace("__no__", str(template_number))
                result_1_max_name = "body.trc.tmpl.__no__.1.result_max".replace("__no__", str(template_number))
                result_1_min_name = "body.trc.tmpl.__no__.1.result_min".replace("__no__", str(template_number))
                result_1_status_name = "body.trc.tmpl.__no__.1.result_status".replace("__no__", str(template_number))
                result_2_name = "body.trc.tmpl.__no__.2.result".replace("__no__", str(template_number))
                result_2_max_name = "body.trc.tmpl.__no__.2.result_max".replace("__no__", str(template_number))
                result_2_min_name = "body.trc.tmpl.__no__.2.result_min".replace("__no__", str(template_number))
                result_2_status_name = "body.trc.tmpl.__no__.2.result_status".replace("__no__", str(template_number))
                result_3_name = "body.trc.tmpl.__no__.3.result".replace("__no__", str(template_number))
                result_3_max_name = "body.trc.tmpl.__no__.3.result_max".replace("__no__", str(template_number))
                result_3_min_name = "body.trc.tmpl.__no__.3.result_min".replace("__no__", str(template_number))
                result_3_status_name = "body.trc.tmpl.__no__.3.result_status".replace("__no__", str(template_number))

                if block.__getitem__(pc_save_flag_name):  # process only if PLC_Save flag is set for given template

                    # read
                    operation_status = block.__getitem__(operation_status_name)
                    operation_type = block.__getitem__(operation_type_name)
                    date_time = block.__getitem__(date_time_name)

                    result_1 = block.__getitem__(result_1_name)
                    result_1_max = block.__getitem__(result_1_max_name)
                    result_1_min = block.__getitem__(result_1_min_name)
                    result_1_status = block.__getitem__(result_1_status_name)
                    result_2 = block.__getitem__(result_2_name)
                    result_2_max = block.__getitem__(result_2_max_name)
                    result_2_min = block.__getitem__(result_2_min_name)
                    result_2_status = block.__getitem__(result_2_status_name)
                    result_3 = block.__getitem__(result_3_name)
                    result_3_max = block.__getitem__(result_3_max_name)
                    result_3_min = block.__getitem__(result_3_min_name)
                    result_3_status = block.__getitem__(result_3_status_name)

                    logger.info("PLC: %s, block: %s, PT: %s, SN: %s, ST: %s, FN: %s" % (self.get_id(), block.get_db_number(), product_type, serial_number, station_number, pc_save_flag_name))

                    self.database_engine.write_operation(product_type, serial_number, week_number, year_number, station_number, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status)

                    self.counter_saved_operations += 1
                    # cancel save flag:
                    block.set_flag(pc_save_flag_name, False)
