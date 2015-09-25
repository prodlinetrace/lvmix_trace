# this is a class of PLC controller
import snap7
import logging
from constants import PC_HEARTBEAT_FLAG, PLC_MESSAGE_FLAG, PLC_SAVE_FLAG, STATION_NUMBER, STATION_STATUS, PRODUCT_TYPE, SERIAL_NUMBER, STATION_STATUS_CODES, STATION_ID, TRC_TMPL_COUNT, TRC_TMPL_SAVE_FLAG, PC_OPEN_BROWSER_FLAG, DATE_TIME, WEEK_NUMBER, YEAR_NUMBER
from plc.util import get_product_id
from plc.datablocks import DataBlocks
from plc.custom_exceptions import UnknownDb
from plc.database import Database
from datetime import datetime
from time import sleep
import webbrowser
import traceback

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
        self.counter_show_product_details = 0
        self._baseurl = 'http://localhosts/app'
        self._popups = True

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
                logger.info("PLC: {plc} connected to server: IP {ip} PORT {port}".format(plc=self, ip=self.__ip, port=self.__port))
            else:
                logger.error("PLC: {plc} connection to server: IP {ip} PORT {port} Failed attempt {item}/{total}".format(plc=self, ip=self.__ip, port=self.__port, item=attempt, total=self._reconnect))
                self.connect(attempt)
                return

    def disconnect(self):
        logger.info("PLC {plc}. disconnection procedure started...".format(plc=self))
        if self.database_engine is not None:
            self.database_engine.disconnect()
        self.client.disconnect()
        self.cancel_pc_busy_flags()

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
            logger.info("PLC: {plc}. Time diff between PLC and PC {delta} is bigger than the trigger {trigger}. Synchronizing.".format(plc=self, delta=abs(delta.total_seconds()), trigger=diff))
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

    def set_baseurl(self, baseurl):
        self._baseurl = baseurl

    def get_baseurl(self):
        return self._baseurl

    def set_popups(self, popups=True):
        self._popups = popups

    def get_popups(self):
        return self._popups


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
        2.4. Open popup window with product details.
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
            self.show_product_details(dbid)
        else:
            self.save_operation(dbid)

    def read_status(self, dbid):
        block = self.get_db(dbid)
        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
            return

        if PLC_MESSAGE_FLAG in block.export():
            if block.__getitem__(PLC_MESSAGE_FLAG):  # get the station status from db
                block.set_pc_ready_flag(False)  # set PC ready flag to False
                # body

                for field in [STATION_ID, STATION_NUMBER, STATION_STATUS, SERIAL_NUMBER, PRODUCT_TYPE]:
                    if field not in block.export():
                        logger.warning("PLC: %s, block: %s, is missing field %s, in block body: %s. Message skipped." % (self.get_id(), block.get_db_number(), field, block.export()))
                        block.set_plc_message_flag(False) # switch off PLC_Query bit
                        block.set_pc_ready_flag(True)  # set PC ready flag back to true
                        return

                try:
                    data = block[PRODUCT_TYPE]
                    product_type = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    product_type = 0
                try:
                    data = block[SERIAL_NUMBER]
                    serial_number = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    serial_number = 0
                try:
                    data = block[STATION_ID]
                    station_id = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_id = 0
                try:
                    data = block[STATION_NUMBER]
                    station_number = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_number = 0
                try:
                    data = block[STATION_STATUS]
                    station_status_initial = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_status_initial = 0

                logger.debug("PLC: {plc}, DB: {db}, PT: {type}, SN: {serial}, trying to read status from database for station: {station}".format(plc=self.get_id(), db=block.get_db_number(), type=product_type, serial=serial_number, station=station_number))
                station_status = self.database_engine.read_status(int(product_type), int(serial_number), int(station_number))

                try:
                    status = STATION_STATUS_CODES[station_status]['result']
                except ValueError, e:
                    logger.warning("PLC: {plc}, DB: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                    status = STATION_STATUS_CODES[99]['result']

                block.store_item(STATION_STATUS, station_status)
                sleep(0.1)  # 100ms sleep requested by Marcin Kusnierz @ 24-09-2015
                # try to read data from PLC as test
                try:
                    data = block[STATION_STATUS]
                    station_status_stored = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_status_stored = 0

                if station_status != station_status_stored:
                    logger.error("PLC: {plc}, DB: {db}, PT: {type}, SN: {serial}, SID: {station_id}, status of station ST: {station_number} from database {station_status} if different than one stored on PLC {station_status_stored} (save on PLC failed.)".format(plc=self.get_id(), db=block.get_db_number(), type=product_type, serial=serial_number, station_id=station_id, station_number=station_number, station_status=station_status, status=status, station_status_initial=station_status_initial, station_status_stored=station_status_stored))
                logger.info("PLC: {plc}, DB: {db}, PT: {type}, SN: {serial}, queried from SID: {station_id}, status of station ST: {station_number} taken from database is: {station_status} ({status}). Initial/Stored Status: {station_status_initial}/{station_status_stored} ".format(plc=self.get_id(), db=block.get_db_number(), type=product_type, serial=serial_number, station_id=station_id, station_number=station_number, station_status=station_status, status=status, station_status_initial=station_status_initial, station_status_stored=station_status_stored))

                self.counter_status_message_read += 1
                block.set_plc_message_flag(False)
                block.set_pc_ready_flag(True)  # set pc_ready flag back to true

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
                block.set_pc_ready_flag(False)  # set PC ready flag to False
                # query controller for required fields...
                for field in [STATION_ID, STATION_STATUS, SERIAL_NUMBER, PRODUCT_TYPE]:
                    if field not in block.export():
                        logger.warning("PLC: %s, block: %s, is missing field %s, in block body: %s. Message skipped." % (self.get_id(), block.get_db_number(), field, block.export()))
                        block.set_plc_save_flag(False)
                        block.set_pc_ready_flag(True)  # set busy flag back to ready
                        return
                try:
                    data = block[PRODUCT_TYPE]
                    product_type = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    product_type = 0
                try:
                    data = block[SERIAL_NUMBER]
                    serial_number = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    serial_number = 0
                try:
                    data = block[STATION_ID]
                    station_id = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_id = 0
                try:
                    data = block[STATION_STATUS]
                    station_status = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_status = 0
                try:
                    status = STATION_STATUS_CODES[station_status]['result']
                except ValueError, e:
                    logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                    status = STATION_STATUS_CODES[99]['result']

                logger.info("PLC: {plc}, block: {block}, PT: {type}, SN: {serial}, ST: {station}, saving status: {station_status} ({status}) to database".format(plc=self, block=block.get_db_number(), type=product_type, serial=serial_number, station=station_id, station_status=station_status, status=status))

                # get additional data from PLC:
                try:
                    data = block[WEEK_NUMBER]
                    week_number = int(data)
                except ValueError, e:
                    logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                    week_number = 0
                try:
                    data = block[YEAR_NUMBER]
                    year_number = int(data)
                except ValueError, e:
                    logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                    year_number = 0
                try:
                    data = block[DATE_TIME]
                    date_time = str(data)
                except ValueError, e:
                    logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                    date_time = str(datetime.datetime.now())

                self.database_engine.write_status(product_type, serial_number, station_id, station_status, week_number, year_number, date_time)
                self.counter_status_message_write += 1
                block.set_plc_save_flag(False)
                block.set_pc_ready_flag(True)  # set PC ready flag back to true
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
            logger.debug("PLC: %s db block: %r tracebility template count: %r" % (self.get_id(), dbid, template_count))

            for template_number in range(0, template_count):
                pc_save_flag_name = TRC_TMPL_SAVE_FLAG.replace("__no__", str(template_number))
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
                    # read basic data
                    # make sure that basic data is set on PLC (skip otherwise)
                    for field in [STATION_ID, SERIAL_NUMBER, PRODUCT_TYPE]:
                        if field not in block.export():
                            logger.warning("PLC: %s, block: %s, is missing field %s, in block body: %s. Message skipped." % (self.get_id(), block.get_db_number(), field, block.export()))
                            return
                    # get some basic data from data block
                    try:
                        data = block[PRODUCT_TYPE]
                        product_type = int(data)
                    except ValueError, e:
                        logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                        product_type = 0
                    try:
                        data = block[SERIAL_NUMBER]
                        serial_number = int(data)
                    except ValueError, e:
                        logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                        serial_number = 0
                    try:
                        data = block[STATION_ID]
                        station_id = int(data)
                    except ValueError, e:
                        logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                        station_id = 0
                    try:
                        data = block[WEEK_NUMBER]
                        week_number = int(data)
                    except ValueError, e:
                        logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                        week_number = 0
                    try:
                        data = block[YEAR_NUMBER]
                        year_number = int(data)
                    except ValueError, e:
                        logger.warning("PLC: {plc}, block: {db} wrong value for status, returning undefined. Exception: {e}".format(plc=self, db=block.get_db_number(), e=e))
                        year_number = 0

                    # read specific data
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

                    logger.info("PLC: {plc}, DB: {db}, PT: {type}, SN: {serial}, ST: {station}, TN: {template_number} FN: {flag}".format(plc=self, db=block.get_db_number(), type=product_type, serial=serial_number, station=station_id, template_number=template_number, flag=pc_save_flag_name))

                    self.database_engine.write_operation(product_type, serial_number, week_number, year_number, station_id, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status)
                    self.counter_saved_operations += 1
                    block.set_flag(pc_save_flag_name, False)  # cancel save flag:

    def show_product_details(self, dbid):
        block = self.get_db(dbid)
        if block is None:
            logger.warn("PLC: %s db block: %r is missing on controller. Skipping" % (self.get_id(), dbid))
            return

        if PC_OPEN_BROWSER_FLAG in block.export():
            if block.__getitem__(PC_OPEN_BROWSER_FLAG):  # get the station status from db
                block.set_pc_ready_flag(False)  # set PC ready flag to False

                try:
                    data = block[PRODUCT_TYPE]
                    product_type = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    product_type = 0
                try:
                    data = block[SERIAL_NUMBER]
                    serial_number = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    serial_number = 0
                try:
                    data = block[STATION_ID]
                    station_id = int(data)
                except ValueError, e:
                    logger.error("Data read error from PLC: {plc} DB: {db} Input: {data} Exception: {e}, TB: {tb}".format(plc=self, db=dbid, data=data, e=e, tb=traceback.format_exc()))
                    station_id = 0
                logger.info("PLC: {plc} ST: {station} PT: {type} SN: {serial} browser opening request - show product details.".format(plc=self.get_id(), station=station_id, type=product_type, serial=serial_number))

                url = "/".join([self.get_baseurl(), 'product', str(get_product_id(product_type, serial_number))])
                if self.get_popups():
                    """
                    In order to open product details in same tab please reconfigure your firefox:
                    1) type about:config in firefox address bar
                    2) set browser.link.open_newwindow property to value 1
                    more info on:
                    http://kb.mozillazine.org/Browser.link.open_newwindow
                    http://superuser.com/questions/138298/force-firefox-to-open-pages-in-a-specific-tab-using-command-line
                    """

                    if webbrowser.open(url):
                        logger.info("PLC: {plc} ST: {station} URL: {url} product details window opened successfully.".format(plc=self.get_id(), station=station_id, type=product_type, serial=serial_number, url=url))
                    else:
                        logger.warning("PLC: {plc} ST: {station} URL: {url} failed to open product details window".format(plc=self.get_id(), station=station_id, type=product_type, serial=serial_number, url=url))
                else:
                    logger.warning("PLC: {plc} ST: {station} URL: {url} Popup event registered but popups are disabled by configuration.".format(plc=self.get_id(), station=station_id, type=product_type, serial=serial_number, url=url))

                self.counter_show_product_details += 1
                block.set_pc_open_browser_flag(False) # cancel PC_OPEN_BROWSER flag
                block.set_pc_ready_flag(True)  # set PC ready flag back to true
