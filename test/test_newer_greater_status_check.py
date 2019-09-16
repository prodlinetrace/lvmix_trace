#!/usr/bin/env python
# TODO: Make it nose / unittest.

import os
import logging
import unittest
logging.root.setLevel(logging.DEBUG)

db_uri='''mysql+pymysql://trace:trace@localhost/trace?autocommit=true'''
os.environ['DATABASE_URL'] = db_uri

from traceability.plc import PLC
from traceability.database import Database

# initialize PLC with db-connection
p = PLC()
p._init_database(db_uri)
print (p)

# define test data
product_id = "46400601205131043619"
station_number = 23
station_number_OK = 24  # this one is the newest status.
station_number_NOK = 31  # there are older and greater statuses than this one.
admin_user_id = 99
status_OK = 1
debug=True


class TestNewerGreaterStatusCheck(unittest.TestCase):
    
    def test_get_newer_greater_status_check_default(self):
        p = PLC()
        p._init_database(db_uri)
        self.assertTrue(p.get_newer_greater_status_check(), "get newer_greater_status_check value (default)")

    def test_set_newer_greater_status_check(self):
        p = PLC()
        p._init_database(db_uri)
        p.set_newer_greater_status_check(False) 
        self.assertFalse(p.get_newer_greater_status_check(), "set newer_greater_status_check value - was set to false")
        
    def test_db_connectivity(self):
        admin_user_id = 99
        self.assertEqual(p.database_engine.get_user_id('admin'), admin_user_id, "Check admin user ID - db connection ok.")

    def test_read_status(self):
        self.assertEqual(p.database_engine.read_status(product_id, station_number), status_OK, "Read the status from product_id: {product_id} station: {station_number} (status: OK)".format(station_number=station_number, product_id=product_id))

    def test_newer_greater_status_positive(self):
        self.assertTrue(p.database_engine.newer_greater_status(product_id, station_number_NOK, debug), "Status on station 23 should have greater statuses with newer timestamps- check positive (NOK)")
    
    def test_newer_greater_status_negative(self):
        self.assertFalse(p.database_engine.newer_greater_status(product_id, station_number_OK, debug), "Status on station 24 should have greater statuses with older timestamps - check negative (OK)")


if __name__ == '__main__':
    unittest.main()