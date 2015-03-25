#!/usr/bin/env python
import logging
import os
import sys
from plc import controller
from plc.prodline import ProdLineBase

logger = logging.getLogger(__name__)


class PlcDbDumper(ProdLineBase):

    def __init__(self, argv, loglevel=logging.WARNING):
        ProdLineBase.__init__(self, argv, loglevel)
        self.set_controller_class(controller.Controller)

    def run(self):
        self.init_controllers()
        self.connect_controllers()
        for _ctrl in self.controllers:
            for _dbno, _db in _ctrl.get_dbs():
                _bytearray = _db.get_bytearray()
                f = os.path.join(os.path.dirname(os.path.abspath(os.path.curdir)), 'data', 'dbdump', _ctrl.get_id() + "_" + str(_dbno) + '.db')
                print "saving data item %s to %s file" % (_dbno, f)
                logger.info("saving data item %s to %s file" % (_dbno, f))
                open(f, "wb").write(_bytearray)
        self.disconnect_controllers()


def main():
    sys.argv.append("-c")
    sys.argv.append("../prodLine.conf")
    dumper = PlcDbDumper(sys.argv, logging.INFO)
    dumper.run()


if __name__ == "__main__":
    sys.exit(main())
