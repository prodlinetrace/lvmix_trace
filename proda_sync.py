#!/usr/bin/env python
#-*- coding: utf-8 -*-
import logging
import sys
from traceability.proda import DatabaseSync

logger = logging.getLogger(__name__)

def main():
    logger.info("Proda Sync Program Started")
    dbsync = DatabaseSync(sys.argv)
    
    dbsync.list_sync_candidates(limit=10)
    product = dbsync.find_sync_data()
    dbsync.sync_single_product(product, dry_run=False)
    #sync.prepare_products_for_proda_sync()
    #sync.sync_all_products()
    logger.info("Proda Sync Program Finished")


if __name__ == "__main__":
    sys.exit(main())
