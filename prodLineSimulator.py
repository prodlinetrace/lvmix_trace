import logging
import sys
import os
from plc.prodline import ProdLineBase
from plc.simulator import Simulator
import time
import snap7

logger = logging.getLogger(__name__)

class ProdLineSimulator(ProdLineBase):

    def __init__(self, argv, loglevel=logging.WARNING):
        ProdLineBase.__init__(self, argv, loglevel)

        self.set_controller_class(Simulator)

    def init_mem_blocks(self):
        for ctrl in self.controllers:
            areaCode = snap7.snap7types.srvAreaDB
            for db in ctrl.get_active_datablock_list():
                _file = os.path.join(os.path.abspath(os.path.curdir), 'data', 'dbdump', ctrl.get_id() + "_" + str(db) + '.db')
                data = bytearray(open(_file, "rb").read())
                ctrl.register_area(areaCode, db, data)
                logger.info("Simulator: %s registered db: %s" % (ctrl, db))
                print "Simulator: %s registered db: %s" % (ctrl, db)

    def run(self):
        # initialize controllers - list of active controllers will be available as self._controlers
        self.init_controllers()
        self.connect_controllers()
        self.init_mem_blocks()
        # do tests
        j = 0
        while j < 100:
            for _sim in self.controllers:
                j += 1
                print "XXXXXXXX", j, _sim
                _sim.run()
            time.sleep(1)

        # close controller connections and exit cleanly
        self.disconnect_controllers()


def main():
    logger.info("Starting test app")
    sys.argv.append("-v")
    prodLine = ProdLineSimulator(sys.argv, logging.DEBUG)
    prodLine.run()
    logger.info("Test app finished")

if __name__ == "__main__":
    sys.exit(main())
