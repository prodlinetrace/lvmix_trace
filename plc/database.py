#!/usr/bin/python
from plc.db_models import *
from plc.util import get_product_id
from datetime import datetime
import sqlalchemy

logger = logging.getLogger(__name__)


class Database(object):

    def __init__(self):
        # force foreign keys constraints. to check the data integrity.
        @sqlalchemy.event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        db.create_all()  # initialize empty database if required.

    def read_status(self, product_type, serial_number, station):
        product_type = int(product_type)
        serial_number = int(serial_number)
        product_id = get_product_id(product_type, serial_number)
        station = int(station)
        res = Status.query.filter_by(product_id=product_id).filter_by(station_id=station).all()
        if len(res) == 0:
            logger.warn("record for PT: %s SN: %s ST: %d not found - returning undefined" % (product_type, serial_number, station))
            return 0  # Wabco statuses are not used anymore. Current statuses: (0 undefined, 1 OK, 2 NOK)
        ret = res[-1].status
        logger.info("record for PT: %s SN: %s ST: %d has status: %s" % (product_type, serial_number, station, ret))
        return ret

    def write_status(self, product_type, serial_number, station, status, week_number=48, year_number=15, date_time=datetime.now()):
        product_type = int(product_type)
        serial_number = int(serial_number)
        product_id = get_product_id(product_type, serial_number)
        station = int(station)
        status = int(status)
        week_number = int(week_number)
        year_number = int(year_number)
        date_time = str(date_time)
        logger.debug("saving record for PT: %s SN: %s ST: %d STATUS: %d  PW:%s PY: %s DT: %s" % (product_type, serial_number, station, status, week_number, year_number, date_time))

        self.add_product_if_required(product_type, serial_number, week_number, year_number)
        self.add_station_if_required(station)
        self.add_operation_status_if_required(status)  # status and operation status names are kept in one and same table
        self.add_status(status, product_id, station, date_time)

    def write_operation(self, product_type, serial_number, week_number, year_number, station_id, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status):
        product_type = int(product_type)
        serial_number = int(serial_number)
        product_id = get_product_id(product_type, serial_number)
        station_id = int(station_id)

        self.add_product_if_required(product_type, serial_number, week_number, year_number)
        self.add_station_if_required(station_id)
        self.add_operation_status_if_required(operation_status)
        self.add_operation_status_if_required(result_1_status)
        self.add_operation_status_if_required(result_2_status)
        self.add_operation_status_if_required(result_3_status)
        self.add_operation_type_if_required(operation_type)
        self.add_operation(product_id, station_id, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status)

    def add_operation(self, product_id, station_id, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status):
        product_id,
        station_id,
        operation_status,
        operation_type,
        result_1,
        result_1_max,
        result_1_min,
        result_1_status,
        result_2,
        result_2_max,
        result_2_min,
        result_2_status,
        result_3,
        result_3_max,
        result_3_min,
        result_3_status
        if date_time is None:
            date_time = str(date_time)

        try:
            new_operation = Operation(product_id, station_id, operation_status, operation_type, date_time, result_1, result_1_max, result_1_min, result_1_status, result_2, result_2_max, result_2_min, result_2_status, result_3, result_3_max, result_3_min, result_3_status)
            logger.info("Adding new Operation to database: {operation}".format(operation=new_operation))
            db.session.add(new_operation)
            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError, e:
                logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: %s is locked. Error: %s" % (db.get_app().config['SQLALCHEMY_DATABASE_URI'], e.__str__()))
            return False
        return True

    def add_status(self, status, product, station, date_time=None):
        status = int(status)
        product = int(product)
        station = int(station)
        if date_time is None:
            date_time = str(date_time)

        try:
            new_status = Status(status, product, station, date_time)
            logger.info("Adding new Status to database: {status}".format(status=new_status))
            db.session.add(new_status)
            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError, e:
                logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: {database} is locked. Error: {error}".format(database=db.get_app().config['SQLALCHEMY_DATABASE_URI'], error=e.__str__()))
            return False
        return True

    def add_product_if_required(self, product_type, serial_number, week_number=48, year_number=15):
        product_type = int(product_type)
        serial_number = int(serial_number)
        week_number = int(week_number)
        year_number = int(year_number)

        try:
            _product = Product.query.filter_by(type=int(product_type)).filter_by(serial=int(serial_number)).first()
            if _product is None:  # add item if not exists yet.
                new_prod = Product(product_type, serial_number, week_number, year_number)
                logger.info("Adding new Product to database: {prod}".format(prod={new_prod}))
                db.session.add(new_prod)
                try:
                    db.session.commit()
                except sqlalchemy.exc.IntegrityError, e:
                    logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: %s is locked. Error: %s" % (db.get_app().config['SQLALCHEMY_DATABASE_URI'], e.__str__()))
            return False
        return True

    def add_station_if_required(self, station):
        station = int(station)
        try:
            _station = Station.query.filter_by(id=int(station)).first()
            if _station is None:  # add new station if required (should not happen often)
                # TODO: try to get ip. port, rack, slot from config file
                new_station = Station(id=station, name=station)
                logger.info("Adding new Station to database: %s" % str(new_station))
                db.session.add(new_station)

            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError, e:
                logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: %s is locked. Error: %s" % (db.get_app().config['SQLALCHEMY_DATABASE_URI'], e.__str__()))
            return False
        return True

    def add_operation_type_if_required(self, operation_type):
        operation_type = int(operation_type)

        try:
            _operation_type = Operation_Type.query.filter_by(id=int(operation_type)).first()
            if _operation_type is None:  # add new operation_type if required (should not happen often)
                new_operation_type = Operation_Type(id=operation_type, name=operation_type)
                logger.info("Adding new Operation_Type to database: %s" % str(new_operation_type))
                db.session.add(new_operation_type)

            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError, e:
                logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: %s is locked. Error: %s" % (db.get_app().config['SQLALCHEMY_DATABASE_URI'], e.__str__()))
            return False
        return True

    def add_operation_status_if_required(self, operation_status):
        operation_status = int(operation_status)

        try:
            _operation_status = Operation_Status.query.filter_by(id=int(operation_status)).first()
            if _operation_status is None:  # add new operation_status if required (should not happen often)
                new_operation_status = Operation_Status(id=operation_status, name=operation_status)
                logger.info("Adding new Operation_Status to database: %s" % str(new_operation_status))
                db.session.add(new_operation_status)

            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError, e:
                logger.error("%s : %s " % (repr(e), e.__str__()))

        except sqlalchemy.exc.OperationalError, e:
            logger.error("Database: %s is locked. Error: %s" % (db.get_app().config['SQLALCHEMY_DATABASE_URI'], e.__str__()))
            return False
        return True

    def get_product_count(self):
        return Product.query.count()

    def get_station_count(self):
        return Station.query.count()

    def get_status_count(self):
        return Status.query.count()

    def get_status_type_count(self):
        return Operation_Status.query.count()

    def get_opertation_count(self):
        return Operation.query.count()

    def get_operation_type_count(self):
        return Operation_Type.query.count()

    def get_comment_count(self):
        return Comment.query.count()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def get_status(self):
        return True

    def initialize_example_data(self):
        db.drop_all()
        db.create_all()
        product_type = 1234567899
        i1 = Product(product_type, 16666, 42, 15)
        i2 = Product(product_type, 26666, 42, 15)
        i3 = Product(product_type, 1234, 42, 15)
        # i4 = Product(16303, "666", "11", "16")
        s10 = Station(10, "192.168.0.10", 102, 0, 2)
        s20 = Station(20, "192.168.0.20", 102, 0, 2)
        s21 = Station(21, "192.168.0.20", 102, 0, 2)
        s22 = Station(22, "192.168.0.20", 102, 0, 2)
        s23 = Station(23, "192.168.0.20", 102, 0, 2)
        # s24 = Station(11, "192.168.0.10", 102, 0, 2)

        t1 = Status(0, get_product_id(product_type, 16666), 10, None)
        t2 = Status(1, get_product_id(product_type, 26666), 20, None)
        t3 = Status(0, get_product_id(product_type, 1234), 10, None)
        t4 = Status(1, get_product_id(product_type, 1234), 20, None)
        t5 = Status(1, get_product_id(product_type, 1234), 21, None)
        t6 = Status(0, get_product_id(product_type, 1234), 21, None)

        db.session.add(i1)
        db.session.add(i2)
        db.session.add(i3)
        # db.session.add(i4)

        db.session.add(s10)
        db.session.add(s20)
        db.session.add(s21)
        db.session.add(s22)
        db.session.add(s23)
        # db.session.add(s24)

        db.session.add(t1)
        db.session.add(t2)
        db.session.add(t3)
        db.session.add(t4)
        db.session.add(t5)
        db.session.add(t6)

        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError, e:
            logger.error("%s : %s " % (repr(e), e.__str__()))
