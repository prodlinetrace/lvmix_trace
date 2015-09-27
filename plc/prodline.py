#!/usr/bin/env python
import time
import logging
from plc.helpers import parse_config, parse_args
import snap7
from plc.database import Database
import threading
import concurrent.futures
import traceback
from datetime import datetime

logger = logging.getLogger(__name__.ljust(12)[:12])


class ProdLineBase(object):

    def __init__(self, argv, loglevel=logging.INFO):
        self._argv = argv
        self._opts, self._args = parse_args(self._argv)

        # handle logging - set root logger level
        logging.root.setLevel(logging.INFO)
        logger = logging.getLogger(__name__)
        logger.setLevel(loglevel)

        # init datetime.strptime so it is available in threads (http://www.mail-archive.com/python-list@python.org/msg248846.html)
        year = datetime.strptime("01","%y")

        # parse config file
        logger.info("Using config file {cfg}.".format(cfg=self._opts.config))
        self._config = parse_config(self._opts.config)
        _fh = logging.FileHandler(self._config['main']['logfile'][0])
        _ch = logging.StreamHandler()
        self.__PLCClass = None
        self._baseurl = 'http://localhost:5000/'
        self._popups  = True
        self._pc_ready_flag_on_poll = False
        self._pollsleep = 0.1
        self._polldbsleep = 0.01

        if self._opts.quiet:
            # log errors to console
            _ch.setLevel(logging.ERROR)
            # log INFO+ to file
            _fh.setLevel(logging.INFO)

        if self._opts.verbose:
            # log INFO+ to console
            _ch.setLevel(logging.INFO)
            # log DEBUG+ to file
            _fh.setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logging.root.setLevel(logging.DEBUG)

        _fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        _ch.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        # logger.addHandler(_fh)
        logging.root.addHandler(_fh)

        self.__ctrl_list = []
        self.controllers = []

    def get_popups(self):
        return self._popups

    def set_popups(self, popups=True):
        logger.info("Popups set to: {popups}".format(popups=popups))
        self._popups = popups

    def get_baseurl(self):
        return self._baseurl

    def set_baseurl(self, baseurl):
        logger.info("Baseurl set to: {baseurl}".format(baseurl=baseurl))
        self._baseurl = baseurl

    def get_pollsleep(self):
        return self._pollsleep

    def set_pollsleep(self, sleep):
        logger.info("pollsleep set to: {sleep}".format(sleep=sleep))
        self._pollsleep = sleep

    def get_polldbsleep(self):
        return self._polldbsleep

    def set_polldbsleep(self, sleep):
        logger.info("polldbsleep set to: {sleep}".format(sleep=sleep))
        self._polldbsleep = sleep

    def get_pc_ready_flag_on_poll(self):
        return self._pc_ready_flag_on_poll

    def set_pc_ready_flag_on_poll(self, flag):
        logger.info("pc_ready_flag_on_poll set to: {flag}".format(flag=flag))
        self._pc_ready_flag_on_poll = flag

    def get_config(self):
        return self._config

    def get_db_file(self):
        return self._config['main']['dbfile'][0]

    def set_controller_class(self, plcClass):
        self.__PLCClass = plcClass

    # start controller connections
    def connect_controllers(self):
        for ctrl in self.__ctrl_list:
            logging.debug("Connecting PLC: {plc} ".format(plc=ctrl.id))
            ctrl.connect()
            logger.info("PLC: {plc} has status: {status} ".format(plc=ctrl.id, status=ctrl.get_status()))
            if ctrl.get_status():
                self.controllers.append(ctrl)
                logger.debug("PLC: {plc} Set as active.".format(plc=ctrl.get_id()))
            else:
                logger.warning("Unable connect to PLC: {plc}. Skipping.".format(plc=ctrl))

    # close controller connections
    def disconnect_controllers(self):
        for ctrl in self.controllers:
            logger.debug("PLC: {plc} disconnecting.".format(plc=ctrl))
            ctrl.disconnect()

    def pc_heartbeat(self):
        for c in self.controllers:
            try:
                c.blink_pc_heartbeat()
            except snap7.snap7exceptions.Snap7Exception:
                logging.critical("Connection to PLC: {plc} lost. Trying to re-establish connection.".format(plc=c))
                c.connect()

    def sync_controllers_time(self):
        for c in self.controllers:
            c.sync_time()

    def sync_controllers_time_if_needed(self):
        for c in self.controllers:
            try:
                c.sync_time_if_needed()
            except snap7.snap7exceptions.Snap7Exception:
                logging.critical("Connection to PLC: {plc} lost. Trying to re-establish connection.".format(plc=c))
                c.connect()

    def init_controllers(self):
        if 'main' not in self._config:
            logger.warning("unable to find section main in configuration. File: {cfg}".format(cfg=self._opts.config))

        if 'controllers' not in self._config['main']:
            logger.warning("unable to find section controllers in configuration main. File: {cfg}".format(cfg=self._opts.config))

        self.__ctrl_list = []

        for ctrl in self._config['main']['controllers']:
            ip = self._config[ctrl]['ip'][0]
            rack = self._config[ctrl]['rack'][0]
            slot = self._config[ctrl]['slot'][0]
            port = self._config[ctrl]['port'][0]
            name = self._config[ctrl]['name'][0]
            iden = self._config[ctrl]['id'][0]
            datablocks = []
            for cblock in self._config[ctrl]['blocks']:
                if cblock in self._config:
                    dbid = int(self._config[cblock]['id'][0])
                    datablocks.append(dbid)
                else:
                    logger.error("PLC: {plc} is configured to use DB: {db} but this DB is missing in configuration file (not defined).".format(plc=ctrl.id, db=cblock))

            if self._config[ctrl]['status'][0] != '1':
                logger.warning("PLC: {plc} is in status: {status} (in configuration file). Skipped.".format(plc=ctrl, status=self._config[ctrl]['status']))
                continue
            c = self.__PLCClass(ip, rack, slot, port)
            c.set_name(name)
            c.set_id(iden)
            logger.debug("PLC: {plc} configuring database engine connectivity".format(plc=ctrl))
            c._init_database(dbfile=self.get_db_file())
            logger.debug("PLC: {plc} set active data blocks to: {dbs}".format(plc=ctrl, dbs=str(datablocks)))
            c.set_active_datablock_list(datablocks)
            logger.debug("PLC: {plc} is configured now.".format(plc=ctrl))

            self.__ctrl_list.append(c)
        return True


class ProdLine(ProdLineBase):

    def __init__(self, argv, loglevel=logging.INFO):
        ProdLineBase.__init__(self, argv, loglevel)
        self.database = Database(self.__class__.__name__)
        from plc.controller import Controller
        self.set_controller_class(Controller)

    def get_status(self):
        return " ".join([str(ctrl.get_id()) + ":" + str(ctrl.get_status()) for ctrl in self.controllers])

    def get_counter_status_message_read(self):
        return sum([ctrl.counter_status_message_read for ctrl in self.controllers])

    def get_counter_status_message_write(self):
        return sum([ctrl.counter_status_message_write for ctrl in self.controllers])

    def get_counter_saved_operations(self):
        return sum([ctrl.counter_saved_operations for ctrl in self.controllers])

    def get_counter_product_details_display(self):
        return sum([ctrl.counter_show_product_details for ctrl in self.controllers])

    def get_product_count(self):
        return self.database.get_product_count()

    def get_station_count(self):
        return self.database.get_station_count()

    def get_status_count(self):
        return self.database.get_status_count()

    def get_opertation_count(self):
        return self.database.get_opertation_count()

    def get_operation_type_count(self):
        return self.database.get_operation_type_count()

    def get_status_type_count(self):
        return self.database.get_status_type_count()

    def get_comment_count(self):
        return self.database.get_comment_count()

    def test_messages(self):
        for ctrl in self.controllers:
            for msg in self._config['main']['messages']:
                dbid = int(self._config[msg]['id'][0])
                message = ctrl.getParsedDb(dbid)
                timestamp = "%.2x-%.2x-%.2x %.2x:%.2x:%.2x.%.4x" % (message.__getitem__('head.time.year'), message.__getitem__('head.time.month'), message.__getitem__('head.time.day'), message.__getitem__('head.time.hour'), message.__getitem__('head.time.minute'), message.__getitem__('head.time.second'), message.__getitem__('head.time.msecond'))
                logger.info("PLC: {plc} DB: {db} has timestamp: {timestamp}".format(plc=ctrl.id, db=dbid, timestamp=timestamp))

    def test_time_get(self):
        for ctrl in self.controllers:
            logger.info("PLC: {plc} system time: {time}".format(plc=ctrl, time=ctrl.get_time()))

    def test_time_set(self):
        dtime = datetime(2015, 04, 01, 22, 12, 13)
        for ctrl in self.controllers:
            logger.info("PLC: {plc} set system time to: {dtime}".format(plc=ctrl, dtime=dtime))
            ctrl.set_time(dtime)

    def test_time_sync(self):
        for ctrl in self.controllers:
            logger.info("PLC: {plc} Sync system time with PC".format(plc=ctrl))
            ctrl.sync_time()

    def test_time(self):
        self.test_time_get()
        self.test_time_set()
        self.test_time_get()
        self.test_time_sync()
        self.test_time_get()

    def poll(self):
        self.pollStatus()
        self.pollOperations()

    def pollStatus(self):
        for ctrl in self.controllers:
            for dbid in ctrl.get_active_datablock_list():
                if dbid != 300:
                    continue
                try:
                    ctrl.poll_db(dbid)
                except snap7.snap7exceptions.Snap7Exception:
                    logging.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                    ctrl.connect()

    def pollOperations(self):
        for ctrl in self.controllers:
            for dbid in ctrl.get_active_datablock_list():
                if dbid == 300:
                    continue
                try:
                    ctrl.poll_db(dbid)
                except snap7.snap7exceptions.Snap7Exception:
                    logging.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                    ctrl.connect()

    def run(self, times=10):
        """"
            runs main loop of the class.
            @param times -  defines how many poll loops should be executed. (0 for infinity)
        """
        logger.info("Polling for {times} times (zero means infinity)".format(times=times))
        i = 0
        while i < times or times == 0:
            self.poll()
            i += 1
            # try to sync controllers every 1000 times if needed - first sync after 5 times.
            if i % 1000 == 5:
                self.sync_controllers_time_if_needed()

            # change the value of PC heartbeat flag
            self.pc_heartbeat()

    def runExtras(self):
        """"
            run extras: in sync controller time and update heartbeat bit.
        """
        i = 0
        while True:
            time.sleep(0.1)
            i += 1
            # try to sync controllers time if needed (every 60s by default) - first sync after 5 sec.
            if i % 600 == 50:
                self.sync_controllers_time_if_needed()
            # change the value of PC heartbeat flag (every 100ms by default)
            self.pc_heartbeat()

        return True

    def runStatusProcessor(self):
        """
            Process db300 statuses in infinite loop.
        """
        while True:
            self.pollStatus()

        return True

    def runOperationProcessor(self):
        """
            Process assembly operations in infinite loop.
        """
        while True:
            self.pollOperations()

        return True

    def runController(self, ctrl):
        logger.info("Started Processing Thread for PLC: {plc}, {dbs}".format(plc=ctrl.id, dbs=ctrl.get_active_datablock_list()))
        # set some initial values
        threading.currentThread().setName(ctrl.get_name())
        ctrl.set_baseurl(self.get_baseurl())  # set baseurl per controller
        ctrl.set_pollsleep(self.get_pollsleep())
        ctrl.set_polldbsleep(self.get_polldbsleep())
        ctrl.set_pc_ready_flag_on_poll(self.get_pc_ready_flag_on_poll())
        #
        while True:
            # blink heartbeat
            try:
                ctrl.blink_pc_heartbeat()
            except snap7.snap7exceptions.Snap7Exception:
                logger.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                ctrl.connect()

            # poll controller
            try:
                ctrl.poll()
            except snap7.snap7exceptions.Snap7Exception:
                logger.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                ctrl.connect()

            # sync time
            try:
                ctrl.sync_time_if_needed()
            except snap7.snap7exceptions.Snap7Exception:
                logger.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                ctrl.connect()

            # get configuration update
            try:
                ctrl.set_popups(self.get_popups())
                # logging.debug("{plc} baseurl: {baseurl} popups: {popups}".format(plc=ctrl, popups=ctrl.get_popups(), baseurl=ctrl.get_baseurl()))
            except snap7.snap7exceptions.Snap7Exception:
                logger.critical("Connection to {plc} lost. Trying to re-establish connection.".format(plc=ctrl))
                ctrl.connect()

        return True

    def main(self):
        # initialize controllers - list of active controllers will be available as self.controllers
        self.init_controllers()
        self.connect_controllers()
        #self.run(0)  # old method

        # start each controller for processing in separate thread.
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ctrl = {executor.submit(self.runController, ctrl): ctrl for ctrl in self.controllers}
            for future in concurrent.futures.as_completed(future_to_ctrl):
                try:
                    data = future.result()
                except Exception as exc:
                    tb = traceback.format_exc()
                    logger.error('Thread {thread} generated an exception: {exc}, {tb}'.format(thread=future, exc=exc, tb=tb))
                else:
                    logger.error("{err}".format(err=data))

        self.disconnect_controllers()
        logger.critical("Something went wrong. Main loop just finished. No controllers started/configured?")
