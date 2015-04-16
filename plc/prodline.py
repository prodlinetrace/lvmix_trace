#!/usr/bin/env python
import time
import logging
import helpers
import snap7
from plc.database import Database

logger = logging.getLogger(__name__)


class ProdLineBase(object):

    def __init__(self, argv, loglevel=logging.INFO):
        self._argv = argv
        self._opts, self._args = helpers.parse_args(self._argv)

        # handle logging - set root logger level
        logging.root.setLevel(logging.INFO)
        logger = logging.getLogger(__name__)
        logger.setLevel(loglevel)

        # parse config file
        logger.debug("using config file %s" % self._opts.config)
        self._config = helpers.parse_config(self._opts.config)
        _fh = logging.FileHandler(self._config['main']['logfile'][0])
        _ch = logging.StreamHandler()
        self.__PLCClass = None

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

    def get_config(self):
        return self._config

    def get_db_file(self):
        return self._config['main']['dbfile'][0]

    def set_controller_class(self, plcClass):
        self.__PLCClass = plcClass

    # start controller connections
    def connect_controllers(self):
        for ctrl in self.__ctrl_list:
            logging.debug("Connecting controller: %s " % ctrl.get_id())
            ctrl.connect()
            logger.info("Controller id: %s has status: %s " % (ctrl.get_id(), ctrl.get_status()))
            if ctrl.get_status():
                self.controllers.append(ctrl)
                logger.debug("Controller id: %s with name: %s. Added to the active ones." % (ctrl.get_id(), ctrl.get_name()))
            else:
                logger.warning("Unable to connect controller id: %s with name: %s. Skipping." % (ctrl.get_id(), ctrl.get_name()))

    # close controller connections
    def disconnect_controllers(self):
        for ctrl in self.controllers:
            ctrl.disconnect()
            logger.debug("Controller id: %s ip: %s port: %s. Disconnected." % (ctrl.get_id(), ctrl.get_ip(), ctrl.get_port()))

    def pc_heartbeat(self):
        for c in self.controllers:
            try:
                c.blink_pc_heartbeat()
            except snap7.snap7exceptions.Snap7Exception:
                logging.critical("Connection to %s lost. Trying to re-establish connection." % c)
                c.connect()

    def sync_controllers_time(self):
        for c in self.controllers:
            c.sync_time()

    def sync_controllers_time_if_needed(self):
        for c in self.controllers:
            try:
                c.sync_time_if_needed()
            except snap7.snap7exceptions.Snap7Exception:
                logging.critical("Connection to %s lost. Trying to re-establish connection." % c)
                c.connect()

    def init_controllers(self):
        if 'main' not in self._config:
            logger.warning("unable to find section main in configuration")

        if 'controllers' not in self._config['main']:
            logger.warning("unable to find section controllers in configuration main")

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
                dbid = int(self._config[cblock]['id'][0])
                datablocks.append(dbid)

            if self._config[ctrl]['status'][0] != '1':
                logger.warning("Controller: %s (id: %s) is in status %s. Skipped" % (ctrl, self._config[ctrl]['id'], self._config[ctrl]['status']))
                continue
            c = self.__PLCClass(ip, rack, slot, port)
            c.set_name(name)
            c.set_id(iden)
            logger.debug("Controller: %s (id: %s) configuring database engine connectivity" % (ctrl, self._config[ctrl]['id']))
            c._init_database(dbfile=self.get_db_file())
            logger.debug("Controller: %s (id: %s) set active data blocks to %s" % (ctrl, self._config[ctrl]['id'], str(datablocks)))
            c.set_active_datablock_list(datablocks)
            logger.debug("Controller: %s (id: %s) configured" % (ctrl, self._config[ctrl]['id']))

            self.__ctrl_list.append(c)
        return True


class ProdLine(ProdLineBase):

    def __init__(self, argv, loglevel=logging.INFO):
        ProdLineBase.__init__(self, argv, loglevel)
        self.database = Database()
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

    def get_product_count(self):
        return self.database.get_product_count()

    def get_station_count(self):
        return self.database.get_station_count()

    def get_status_count(self):
        return self.database.get_station_count()

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
                logger.info("PLC: %s message: %s has timestamp: %s" % (ctrl.get_id(), dbid, timestamp))

    def test_time_get(self):
        for ctrl in self.controllers:
            logger.info("PLC: %s system time: %s" % (ctrl, ctrl.get_time()))

    def test_time_set(self):
        from datetime import datetime
        dtime = datetime(2015, 04, 01, 22, 12, 13)
        for ctrl in self.controllers:
            logger.info("PLC: %s set system time to: %s" % (ctrl, dtime))
            ctrl.set_time(dtime)

    def test_time_sync(self):
        for ctrl in self.controllers:
            logger.info("PLC: %s Sync system time with PC" % ctrl)
            ctrl.sync_time()

    def test_time(self):
        self.test_time_get()
        self.test_time_set()
        self.test_time_get()
        self.test_time_sync()
        self.test_time_get()

    def poll(self):
        for ctrl in self.controllers:
            for dbid in ctrl.get_active_datablock_list():
                try:
                    ctrl.poll_db(dbid)
                except snap7.snap7exceptions.Snap7Exception:
                    logging.critical("Connection to %s lost. Trying to re-establish connection." % ctrl)
                    ctrl.connect()

    def run(self, runtime=10, frequency=10):
        """"
            runs main loop of the class.
            @param time [s] defines how log loop should last. (0 for infinity)
            @param frequency [Hz] defines controller poll frequency
        """
        logger.info("Polling for %d[s] with frequency %d[Hz]" % (runtime, frequency))
        times = runtime * frequency
        i = 0
        while i < times or runtime == 0:
            self.poll()
            time.sleep(float(1) / frequency)
            i += 1

            # try to sync controllers time if needed (every 60s by default) - first sync after 5 sec.
            if i % 600 == 50:
                self.sync_controllers_time_if_needed()

            # change the value of PC heartbeat flag (every 100ms by default)
            self.pc_heartbeat()

    def main(self):
        # initialize controllers - list of active controllers will be available as self.controllers
        self.init_controllers()
        self.connect_controllers()
        self.run(0)
        # close controller connections and exit cleanly
        self.disconnect_controllers()
