#!/usr/bin/env python
#-*- coding: utf-8 -*-
import logging
import sys
from traceability.proda import Sync

logger = logging.getLogger(__name__)

def main():
    logger.info("Proda Sync Program Started")
    logging.info("Starting main app")
    sync = Sync(sys.argv)
    sync.find_sync_data()
    #sync.prepare_products_for_proda_sync()
    #sync.sync_all_products()
    logger.info("Proda Sync Program Finished")


if __name__ == "__main__":
    sys.exit(main())
