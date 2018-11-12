import logging
from .helpers import parse_config, parse_args
from .models import *
import tempfile
import csv
import os
import subprocess
import datetime
import textwrap

logger = logging.getLogger(__name__)


class ProdaProcess(object):
    """
        class that represents Proda Process - used for generating set of PL-SQL inserts to PRODA, one insert per Process Step (PS): 
        Example: 

        insert into
            prodang_convert.vw_test_lvmix
            (
                WABCO_NUMBER,SERIAL_NUMBER,XCOMMENT,PROCESS_STEP_SEQUENCE,
                PROCESS_START_TIME,PROCESS_END_TIME,PROCESS_STATUS,
                PROCESS_STEP_START_TIME,PROCESS_STEP_END_TIME,PROCESS_STEP_STATUS,OPERATOR_ID,
                RESULT_001,RESULT_005,RESULT_011,RESULT_013,RESULT_015,RESULT_016,RESULT_017,RESULT_018
            )
            values
            (
                '4640061000','2018_42_0_123456','46400650001234564218',14,
                to_date('2018-08-03 16:03:02','YYYY-MM-DD HH24:MI:SS'),null,2,
                to_date('2018-08-03 16:03:02','YYYY-MM-DD HH24:MI:SS'),to_date('2018-08-03 16:07:42','YYYY-MM-DD HH24:MI:SS'),1,3242,
                'TS_1_1','TV_1_1_1_12.432','TV_1_2_1_-0.032','TS_2_1','TV_2_1_1_142.432','TV_2_2_1_-40.0432','TV_2_3_1_54.432','TV_2_4_1_345'
            );
    """
    #from models import Product, Status, Operation
    
    def __init__(self, product):
        self.product = product
        self.proda_serial = self.product.proda_serial
        self.statuses = self.product.statuses.all()
        self.operations = self.product.operations.all()
        self.statuses.sort(key=lambda r: r.station_id, reverse=False)
        self.operations.sort(key=lambda r: r.station_id, reverse=False)
        self.process_steps = []
        self.proda_inserts = []
        self.prepare_data()

    def dump_process_steps(self):
        for ps in self.process_steps:
            print ps

    def dump_proda_inserts(self):
        for pi in self.proda_inserts:
            print pi
        
    def get_process_list(self):
        return [ x.station_id for x in self.statuses ]

        
    def prepare_data(self):
        self.process_steps = []  # reset process step list
        for status in self.statuses:
            ps = {}  # process step
            ps['station_id'] = status.station_id
            ps['status_object'] = status
            ps['ps_status'] = StatusCodeConverter.tace_to_wabco_status(status.status)  # save process_step status
            ps['ps_date_added'] = status.date_time
            ps['ps_end_time'] = datetime.datetime.strptime(ps['ps_date_added'], "%Y-%m-%d %H:%M:%S.%f")
            ps['ps_end_time_proda_string'] = "to_date('{0}','YYYY-MM-DD HH24:MI:SS')".format(ps['ps_end_time'].strftime("%Y-%m-%d %H:%M:%S"))
            ps['ps_start_time_proda_string'] = "to_date('{0}','YYYY-MM-DD HH24:MI:SS')".format((ps['ps_end_time'] - datetime.timedelta(minutes=1,seconds=1)).strftime("%Y-%m-%d %H:%M:%S"))  # by default process last 61 seconds
            #ps['process_start_time'] = ''
            ps['process_start_time_proda_string'] = 'null'
            #ps['process_end_time'] = ''
            ps['process_end_time_proda_string'] = 'null'
            if ps['station_id'] == 11:  # station 11 defines process start time
                ps['process_start_time'] = datetime.datetime.strptime(ps['ps_date_added'], "%Y-%m-%d %H:%M:%S.%f")
                ps['process_start_time_proda_string'] = "to_date('{0}','YYYY-MM-DD HH24:MI:SS')".format(ps['process_start_time'].strftime("%Y-%m-%d %H:%M:%S"))
            if ps['station_id'] == 55:  # station 55 defines process end time
                ps['process_end_time'] = datetime.datetime.strptime(ps['ps_date_added'], "%Y-%m-%d %H:%M:%S.%f")
                ps['process_end_time_proda_string'] = "to_date('{0}','YYYY-MM-DD HH24:MI:SS')".format(ps['process_end_time'].strftime("%Y-%m-%d %H:%M:%S"))

            ps_sequence = status.station_id
            if ps_sequence in [100, 101, 102, 103]:
                ps_sequence = 50  # ugly hack to change ps_sequence number for testers 
            ps['ps_sequence'] = ps_sequence
            ps['operator_id'] = status.user_id or 0
            ps['results'] = []
            
            # calculate overal process status # 2 - ongoing, 1 - OK, 0 - NOK
            ps['process_status'] = 2
            if status.station_id in [61, 100, 101, 102, 103]:  # tester or rework station should never set the overal process status
                ps['process_status'] = 'null'
            if ps['station_id'] == 55:  # electronic - only this station can finally set status to 1 (OK)
                ps['process_status'] = StatusCodeConverter.tace_to_wabco_p_status(status.status)  # make sure it's not zero. (1, or 2 only)
            
            # add overal status
            ps['results'].append("TS_{ts_order}_{ts_status}".format(ts_order=100, ts_status=StatusCodeConverter.tace_to_wabco_ps_status(status.status)))  # ts_order = 100 - means status
            ps['results'].append("TV_{ts_order}_{tv_sequence}_{tv_status}_{tv_value}".format(ts_order=100, tv_sequence=1, tv_status=StatusCodeConverter.tace_to_wabco_ps_status(status.status), tv_value=StatusCodeConverter.tace_to_wabco_ps_status(status.status)))  # ts_order = 100 - means status
            
            if status.station_id in [55, 61]:  # add operator id as result in case of station 55 and 61
                ps['results'].append("TS_{ts_order}_{ts_status}".format(ts_order=1000, ts_status=1))  # ts_order = 1000 - means operator number
                ps['results'].append("TV_{ts_order}_{tv_sequence}_{tv_status}_{tv_value}".format(ts_order=1000, tv_sequence=1, tv_status=1, tv_value=ps['operator_id']))  # ts_order = 1000 - means operator number
            
            if status.station_id in [61]:
                pass
                # TODO implemnt comment - analysis
            
            # process operation results
            operations = filter(lambda x: x.station_id == status.station_id, self.operations)  # filter operations with matching station_id
            # filter out operations with with time difference bigger than 120 seconds. 
            operations = filter(lambda x: (ps['ps_end_time'] - datetime.datetime.strptime(x.date_time, "%Y-%m-%d %H:%M:%S.%f")).seconds < 120, operations)
            ps['operations'] = operations
            # find oldest operation and use it as: ps_start_time
            if operations:
                oldest_operation_date = min(operations, key=lambda x: x.date_time).date_time
                ps['ps_start_time'] = datetime.datetime.strptime(oldest_operation_date, "%Y-%m-%d %H:%M:%S.%f")
                ps['ps_start_time_proda_string'] = "to_date('{0}','YYYY-MM-DD HH24:MI:SS')".format(ps['ps_start_time'].strftime("%Y-%m-%d %H:%M:%S"))
                
            
            for operation in operations:
                ps['results'].append("TS_{ts_order}_{ts_status}".format(ts_order=operation.operation_type_id, ts_status=operation.operation_status_id))
                if not operation.result_1_status_id == 1000 and not operation.result_1 == operation.result_1_max == operation.result_1_min == 0:  # skip operations with limits and result == 0 and skip status_id == 1000
                    result_status_1 = 1 if operation.result_1_max > operation.result_1 > operation.result_1_min else 0  # calculate status according to limits (already set as proda kind of values)
                    ps['results'].append("TV_{ts_order}_{tv_sequence}_{tv_status}_{tv_value}".format(ts_order=operation.operation_type_id, tv_sequence=1, tv_status=result_status_1, tv_value=operation.result_1))
                if not operation.result_2_status_id == 1000 and not operation.result_2 == operation.result_2_max == operation.result_2_min == 0:  # skip operations with limits and result == 0 and skip status_id == 1000
                    result_status_2 = 1 if operation.result_2_max > operation.result_2 > operation.result_2_min else 0  # calculate status according to limits (already set as proda kind of values)
                    ps['results'].append("TV_{ts_order}_{tv_sequence}_{tv_status}_{tv_value}".format(ts_order=operation.operation_type_id, tv_sequence=2, tv_status=result_status_2, tv_value=operation.result_2))
                if not operation.result_3_status_id == 1000 and not operation.result_3 == operation.result_3_max == operation.result_3_min == 0:  # skip operations with limits and result == 0 and skip status_id == 1000
                    result_status_3 = 1 if operation.result_3_max > operation.result_3 > operation.result_3_min else 0  # calculate status according to limits (already set as proda kind of values)
                    ps['results'].append("TV_{ts_order}_{tv_sequence}_{tv_status}_{tv_value}".format(ts_order=operation.operation_type_id, tv_sequence=3, tv_status=result_status_3, tv_value=operation.result_3))

            self.process_steps.append(ps)
            self.prepare_proda_inserts()
    
    def prepare_proda_inserts(self):
        self.proda_inserts = []
        for ps in self.process_steps:
            insert = self.get_proda_insert(ps)
            self.proda_inserts.append(insert)
        
        return self.proda_inserts
            
        
    def get_proda_inserts(self):
        return self.proda_inserts
        
    def get_proda_insert(self, ps):
        # TODO: use prepare statement
        RESULTS = ''
        for r in xrange(len(ps['results'])):
            RESULTS += 'RESULT_{number}, '.format(number=str(r+1).zfill(3)) 
        RESULTS = RESULTS.rstrip(', ')  # remove unwanted characters from end of string.
        
        
        insert = """
            insert into
                prodang_convert.vw_test_lvmix
                (
                    WABCO_NUMBER,SERIAL_NUMBER,XCOMMENT,PROCESS_STEP_SEQUENCE,
                    PROCESS_START_TIME,PROCESS_END_TIME,PROCESS_STATUS,
                    PROCESS_STEP_START_TIME,PROCESS_STEP_END_TIME,PROCESS_STEP_STATUS,OPERATOR_ID,
                    {__RESULTS__}
                )
                values
                (
                    '{WABCO_NUMBER}','{SERIAL_NUMBER}','{XCOMMENT}',{PROCESS_STEP_SEQUENCE},
                    {PROCESS_START_TIME},{PROCESS_END_TIME},{PROCESS_STATUS},
                    {PROCESS_STEP_START_TIME},{PROCESS_STEP_END_TIME},{PROCESS_STEP_STATUS},{OPERATOR_ID},
                    {__RESULTS_VALUES__}
                );
        
        """.format(WABCO_NUMBER=self.product.type, SERIAL_NUMBER=self.product.proda_serial, XCOMMENT=self.product.id, PROCESS_STEP_SEQUENCE=ps['ps_sequence'],
                    PROCESS_START_TIME=ps['process_start_time_proda_string'], PROCESS_END_TIME=ps['process_end_time_proda_string'], PROCESS_STATUS=ps['process_status'],
                    PROCESS_STEP_START_TIME=ps['ps_start_time_proda_string'], PROCESS_STEP_END_TIME=ps['ps_end_time_proda_string'], PROCESS_STEP_STATUS=ps['ps_status'], OPERATOR_ID=ps['operator_id'],
                    __RESULTS__= RESULTS, __RESULTS_VALUES__= str(ps['results']).replace('[','').replace(']',''),
        )
        
        return textwrap.dedent(insert)
                


class StatusCodeConverter(object):
    """
    Statusy Trace:
        0 - UNDEFINED
        1 - OK
        2 - NOK
        4 - NOTAVAILABLE
        5 - REPEATEDOK
        6 - REPEATEDNOK
        9 - WAITINIG
        10 - INTERRUPTED
        11 - REPEATEDINTERRUPTED
        99 - VALUEERROR

    Statusy WABCO:
        0 - NOK
        1 - OK
        2 - w trakcie produkcji WIP
        3 - w trakcie produkcji powtorka
        5 - OK powtorzony
        6 - NOK powtorzony
        10 - przerwany test
        11 - przerwany powtorzony
        1000 - nie okreslony
        Dodatkowo 100 + powyzsza wartosc dla 'testowania' stanowiska - aby nie uwzgledniac w statystykach. Czyli np. sprawdzamy reaklamacje i chcemy zapisac wyniki ale nie chcemy wplywac na wskazniki
    """
    STATUS_CODES = [
        {"result": "UNDEFINED", "desc": "status undefined (not present in database)", "trace": 0, "wabco": 1000, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "OK", "desc": "Status ok", "trace": 1, "wabco": 1, "wabco_process_step": 1, "wabco_process": 1},
        {"result": "NOK", "desc": "Status not ok", "trace": 2, "wabco": 0, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "NOTAVAILABLE", "desc": "Not present in given type", "trace": 4, "wabco": 4, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "REPEATEDOK", "desc": "Repeated test was ok", "trace": 5, "wabco": 5, "wabco_process_step": 1, "wabco_process": 1},
        {"result": "REPEATEDNOK", "desc": "Repeated test was not ok", "trace": 6, "wabco": 6, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "WAITING", "desc": "status reset - PLC set status to 'WAITING' and waiting for PC response", "wabco": 9, "trace": 9, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "INTERRUPTED", "desc": "Test was interrupted", "trace": 10, "wabco": 10, "wabco_process_step": 0, "wabco_process": 2},
        {"result": "REPEATEDINTERRUPTED", "desc": "Repeated test was interrupted", "trace": 11, "wabco": 11,  "wabco_process_step": 0, "wabco_process": 2},
        {"result": "VALUEERROR", "desc": "Faulty value was passed. Unable to process data.", "trace": 99, "wabco": 99, "wabco_process_step": 0, "wabco_process": 2},
    ]

    @staticmethod
    def tace_to_wabco_status(st):
        """
        translates trace status code to wabco status code
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['trace']:
                return code['wabco']
        return st

    @staticmethod
    def wabco_to_trace_status(st):
        """
        translates wabco status code to trace status code
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['wabco']:
                return code['trace']
        return st

    @staticmethod
    def tace_to_wabco_ps_status(st):
        """
        translates trace status code to wabco status code - for process step only
        
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['trace']:
                return code['wabco_process_step']
        return st

    @staticmethod
    def wabco_ps_to_trace_status(st):
        """
        translates trace status code to wabco status code - for process step only
        
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['wabco_process_step']:
                return code['trace']
        return st

    @staticmethod
    def tace_to_wabco_p_status(st):
        """
        translates trace status code to wabco status code - for complete process only
        
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['trace']:
                return code['wabco_process']
        return st

    @staticmethod
    def wabco_p_to_trace_status(st):
        """
        translates trace status code to wabco status code - for complete process only
        
        """

        for code in StatusCodeConverter.STATUS_CODES:
            if st == code['wabco_process']:
                return code['trace']
        return st


class Sync(object):


    def __init__(self, argv, loglevel=logging.INFO):
        self.sync_success_count = 0
        self.sync_failed_count = 0
        self.time_started = datetime.datetime.now()
        self._argv = argv
        self._opts, self._args = parse_args(self._argv)
        self.cleanup = False

        self.logger = logging.getLogger(__name__.ljust(24)[:24])
        self.logger.setLevel(logging.DEBUG)

        # parse config file
        self.logger.info("Using config file: {cfg}.".format(cfg=self._opts.config))
        self._config = parse_config(self._opts.config)
        #_fh = TimedRotatingFileHandler(self._config['main']['logfile'][0], when="MIDNIGHT", interval=1, backupCount=30)
        _fh = logging.FileHandler(self._config['main']['logfile'][0])
        _fh.setLevel(logging.DEBUG)
        _ch = logging.StreamHandler()
        _ch.setLevel(logging.INFO)

        if self._opts.quiet:
            # log errors to console
            _ch.setLevel(logging.ERROR)
            # log INFO+ to file
            _fh.setLevel(logging.INFO)

        if self._opts.verbose:
            self.logger.setLevel(logging.DEBUG)
            # log INFO+ to console
            _ch.setLevel(logging.DEBUG)
            # log DEBUG+ to file
            _fh.setLevel(logging.DEBUG)

        _fh.setFormatter(logging.Formatter('%(asctime)s - %(name)-22s - %(levelname)-8s - %(message)s'))
        _ch.setFormatter(logging.Formatter('%(name)s - %(levelname)8s - %(message)s'))
        self.logger.addHandler(_fh)
        self.logger.addHandler(_ch)
        self.logger.info("Using DB: {db}".format(db=self._config['main']['dburi'][0]))

        # cleanup (tmp csv handling)
        cleanup = self._config['main']['cleanup'][0]
        if int(cleanup) == 0:
            self.cleanup = False

        if int(cleanup) == 1:
            self.cleanup = True

        # product timeout in minutes (sync will be triggered once product will not reach station 55 within timeout.)
        self.product_timeout = 480
        if 'product_timeout' in self._config['main']:
            self.product_timeout = int(self._config['main']['product_timeout'][0])

    def get_conf(self):
        return self._config

    def get_conf_file_name(self):
        return self._opts.config



    def get_product_station_status(self, wabco_id, serial, station_id):
        # wabco_id = '4640062010'
        # serial = '000024'
        # station_id = 11
        item = Product.query.filter_by(type=wabco_id).filter_by(serial=serial).first()

        st = 1000  # set status to undefined first
        result = 0  # Test step value result - set to failed. Result has to be either 0 (NOK) or 1 (OK).
        for status in item.statuses.filter_by(station_id=station_id).all():
            st = status.status
            # set result to ok - in case station status is ok or repeatedok
            if st == 1 or st == 5:
                result = 1

        st = self.StatusCodeConverter.tace_to_wabco_status(st)

        return st, [result]

    def get_product_operation_data(self, wabco_id, serial, operation_id):
        # wabco_id = '4640062010'
        # serial = '000024'
        # operation_id = 1480
        item = Product.query.filter_by(type=wabco_id).filter_by(serial=serial).first()

        st = 1000  # set status to undefined first
        results = [0,0,0]
        for operation in item.operations.filter_by(operation_type_id=operation_id).all():
            st = operation.operation_status_id
            results = [0,0,0]
            if not operation.result_3 == operation.result_3_max == operation.result_3_min == 0:
                results.insert(0,operation.result_3)
            if not operation.result_2 == operation.result_2_max == operation.result_2_min == 0:
                results.insert(0,operation.result_2)
            if not operation.result_1 == operation.result_1_max == operation.result_1_min == 0:
                results.insert(0,operation.result_1)

        st = StatusCodeConverter.tace_to_wabco_status(st)

        return st, results

    def product_sync(self, wabco_id, serial):
        if wabco_id == "0":
            return 0

        if wabco_id in self._config:
            msg = "wabco_id: {wabco_id} found in config file: {config_file}".format(wabco_id=wabco_id, config_file=self.get_conf_file_name())
            self.logger.debug(msg)
            is_active = int(self._config[wabco_id]['active'][0])
            if is_active != 1:
                msg = "wabco_id: {wabco_id} is not set to active in: {config_file}".format(wabco_id=wabco_id, config_file=self.get_conf_file_name())
                self.logger.warn(msg)
                return 130
        else:
            msg = "unable to find wabco_id: {wabco_id} in config file: {config_file}. Need to skip it. Sorry!".format(wabco_id=wabco_id, config_file=self.get_conf_file_name())
            self.logger.error(msg)
            return 120

        csv_file = self.generate_csv_file(wabco_id, serial)
        if os.path.exists(csv_file):
            self.logger.debug("psark csv file generated: {csv_file}".format(csv_file=csv_file))
        else:
            self.logger.error("unable to find psark csv file generated: {csv_file}".format(csv_file=csv_file))
            return 2

        return self.run_psark(wabco_id, serial, csv_file)

    def generate_csv_file(self, wabco_id, serial):
        csv_file_name = tempfile.mktemp(suffix=".csv", prefix="psark-{wid}-{sn}-".format(wid=wabco_id, sn=serial))

        test_steps = self._config[wabco_id]['proda_sequence']
        for ts in test_steps:
            ts_cfg = self._config[ts]
            ts_type = ts_cfg['type'][0]
            ts_name = ts_cfg['name'][0]
            ts_desc = ts_cfg['description'][0]
            ts_id = int(ts_cfg['id'][0])
            ts_tv_count = int(ts_cfg['test_values'][0])

            status = -1
            tvs = [0,0,0]
            if ts_type == 'status':
                status, tvs = self.get_product_station_status(wabco_id, serial, ts_id)
            if ts_type == 'operation':
                status, tvs= self.get_product_operation_data(wabco_id, serial, ts_id)
            tv = tvs[:ts_tv_count]

            self.logger.debug("TS found in db. WI: {wabco_id} SN: {serial} TS_ID: {ts_id} TS_DESC: {ts_desc} ST: {status} TV: {tv}".format(wabco_id=wabco_id, serial=serial, ts_id=ts_id, ts_desc=ts_desc, status=status, tv=tv))

            with open(csv_file_name, 'ab') as csvfile:
                result_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                result_writer.writerow([status] + tv)

        return csv_file_name

    def run_psark(self, wabco_id, serial, csv_file):
        psark_exe = self._config['main']['psark'][0]
        db_user = self._config['main']['db_user'][0]
        db_pass = self._config['main']['db_pass'][0]
        db_name = self._config['main']['db_name'][0]
        cmd = [psark_exe, '-c', 'csv_feed', '-f', csv_file, '-u', db_user, '-p', db_pass, '-d', db_name, '-w', wabco_id, '-s', serial]
        self.logger.info("Running command: {cmd}".format(cmd=" ".join(cmd)))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        out, err = p.communicate()

        self.logger.debug(out)

        if self.cleanup:
            os.unlink(csv_file)
            self.logger.debug("CSV file removed: {csv}".format(csv=csv_file))
        else:
            self.logger.warn("CSV file not removed: {csv}".format(csv=csv_file))

        return p.returncode

    def get_products(self, date_string="2017-06-29 06:39:38.973000"):
        """
            gets products from DB younger than given date
        """
        
        candidates = Product.query.filter_by(prodasync=0).order_by(Product.date_added).all()
        
        return candidates


    def find_sync_data(self):
        from models import Product, Status, Operation
        
        #print StatusCodeConverter.tace_to_wabco_status(1)
        """
            this function finds data that needs to be synchronized to PRODA
        """
        
        #candidates = Product.query.filter_by(prodasync=0).order_by(Product.date_added).filter_by(type="4640061000").limit(100).all()  # TEST: limit to test type only
        #candidates = Product.query.filter_by(prodasync=2).order_by(Product.date_added).filter_by(type="4640060020").filter_by(serial="630233").all()  # TEST: limit to test type only - ok
        #candidates = Product.query.filter_by(prodasync=2).order_by(Product.date_added).filter_by(type="4640060020").filter_by(serial="630168").all()  # TEST: limit to test type only - with test failure
        candidates = Product.query.filter_by(prodasync=0).order_by(Product.date_added).filter_by(type="4640061000").filter_by(serial="617803").all()  # TEST: limit to test type only - with test failure
        #candidates = [candidates[:100]]  # hack to get right candidate
        print candidates
        #return 0
        product_to_sync = candidates[0]
        
        self.sync_single_product(product_to_sync)


    def sync_single_product(self, product):
        from models import Product, Status, Operation

        PP = ProdaProcess(product)
        
        print PP.get_process_list()
        #PP.dump_process_steps()
        PP.dump_proda_inserts()
        #insert = PP.get_proda_insert()
        #print insert
        
        
        return 
        

    def prepare_products_for_proda_sync(self):
        """
        This function iterates over database and finds products that finished assembly process.
        Such products are getting prodasync flag set to 1.
        Both failed and successfully completed products get synced.
        Only products with prodasyncflag==0 should be considered.
        Products with prodasync flag set to 1 are processed by sync_all_products method.

        # prodasync flag values
        # 0 - default
        # 1 - ready to sync - should be set once assembly is complete
        # 2 - sync completed successfully
        # 3 - sync failed.

        """

        """
        Osobiscie sklanialem sie w strone nastepujacego rozwiazania:
        - zawor przeszedl stacje 55 - wyzwalaj synchronizacje
        - Jezeli status montazu na dowolnej stacji jest NOK - montaz zostaje przerwany - wyzwalaj synchronizacje
        - jezeli status montazu zaworu na dowolnej stacji jest OK wstrzymaj sie z syncronizacja danych do momentu az zawor dotrze do stacji 55.
        - jezeli status montazu zaworu na dowolnej stacji jest OK i zawor nie przeszedl przez stacje 55 w ciagu 24h - cos jest nie tak - wyzwalaj synchronizacje.

        """
        #candidates = Product.query.filter_by(prodasync=0).order_by(Product.date_added).filter_by(type="4640062010").all()  # TEST: limit to test type only
        candidates = Product.query.filter_by(prodasync=0).order_by(Product.date_added).all()
        for candidate in candidates:
            last_status = candidate.statuses.order_by(Status.id.desc()).first()

            # product just passed station 55 - trigger sync
            if last_status is None:
                self.logger.warn("Product: {product} has no status stored.".format(product=candidate.id))
                continue

            if last_status.station_id == 55:
                candidate.prodasync = 1
                self.logger.debug("Product: {product} set as ready to sync as it just passed station 55.".format(product=candidate.id))
                continue

            # if last status is NOK set ready to sync.
            if last_status.status == 2:
                candidate.prodasync = 1
                self.logger.debug("Product: {product} set as ready to sync due to last status set to NOK.".format(product=candidate.id))
                continue

            # product status is OK but it did not reached station 55 within 24h.
            try:
                last_status_update = datetime.datetime.now() - datetime.datetime.strptime(last_status.date_time, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError, e:
                self.logger.error("Unable to convert date: {date} with format '%Y-%m-%d %H:%M:%S.%f'. Set to timeout".format(date=last_status.date_time))
                last_status_update = datetime.datetime.now() - datetime.datetime(2015, 1, 1)

            if last_status_update.total_seconds() / 60 > self.product_timeout:
                candidate.prodasync = 1
                self.logger.debug("Product: {product} set as ready to sync as it did not reached station 55 within {timeout} minutes.".format(product=candidate.id, timeout=self.product_timeout))
                continue

            # not yet ready to sync
            self.logger.debug("Product: {product} is not yet ready to sync.".format(product=candidate.id))

        # store db session modifications to the file.
        db.session.commit()
        return 0

    def sync_all_products(self):
        #wabco_id = '4640062010'
        # prodasync column description
        # 0 - default
        # 1 - ready to sync - should be set once assembly is complete
        # 2 - sync completed successfully
        # 3 - sync failed.

        items = Product.query.filter_by(prodasync=1).order_by(Product.date_added).all()
        self.logger.info("Found: {number} products to sync".format(number=len(items)))
        for item in items:
            self.logger.info("Starting sync of: {id} PT: {type} SN: {sn} PRODA_SYNC_STAT: {prodasync}".format(id=item.id, type=item.type, sn=item.serial, prodasync=item.prodasync))
            status = self.product_sync(item.type, item.serial)
            if status == 0:
                self.sync_success_count += 1
                item.prodasync = 2
                self.logger.info("Completed sync of: {id} PT: {type} SN: {sn}. Sync Status: {status}".format(id=item.id, type=item.type, sn=item.serial, status=status))
            else:
                self.sync_failed_count += 1
                item.prodasync = 3
                self.logger.error("Failed sync of: {id} PT: {type} SN: {sn}. Sync Status: {status}".format(id=item.id, type=item.type, sn=item.serial, status=status))
            db.session.commit()

        db.session.commit()
        self.logger.info("Sync of {number} products finished in {time}. Stats: {failed} failed / {success} succeed.".format(number=len(items), failed=self.sync_failed_count, success=self.sync_success_count, time=datetime.datetime.now()-self.time_started))

        return 0
