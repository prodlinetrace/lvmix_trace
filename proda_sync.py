#!/usr/bin/env python2
import logging
import sys
import os
import configargparse
import textwrap
from argparse import RawTextHelpFormatter

logger = logging.getLogger(__name__)


def get_help(prog_name='executable'):
    h = """
        To list available products please execute:
        {prog_name} list-products

        To sync one selected product please execute:
        {prog_name} sync-one-product

        To sync all products please execute:
        {prog_name} sync-all
        
        To remove old records please execute:
        {prog_name} remove-old-records

    """.format(prog_name=prog_name)

    return textwrap.dedent(h)


def parse_args():
    prog_name = os.path.basename(sys.argv[0])
    file_name, file_extension = os.path.splitext(prog_name)
    conf_file = os.path.join(".".join([file_name, "conf"]))
    log_file = os.path.join(".".join([file_name, "log"]))
    p = configargparse.ArgParser(
        default_config_files=['~/.my_conf', conf_file],
        description="Tool to manage tracedb - proda sync operations.\n\n",
        epilog=get_help(prog_name),
        formatter_class=RawTextHelpFormatter,
    )
    
    p.add_argument('command', help='command to execute', choices=['list-products', 'sync-one-product', 'sync-all', 'remove-old-records'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('--logfile', required=True, type=str, default=log_file, help='logfile path')
    p.add_argument('--loglevel', action="store", required=False, type=int, default=logging.INFO, help='URI for tracedb connectivity')
    p.add_argument('-v', help='verbose mode', action='store_true')
    p.add_argument('-q', help='quiet mode', action='store_true')
    p.add_argument('--limit', required=False, type=int, default=10, help='Limit number of returned records.')
    p.add_argument('--dburi', required=True, type=str, help='URI for tracedb connectivity')
    p.add_argument('--proda_uri', required=True, type=str, help='URI for PRODA connectivity')
    p.add_argument('--product_timeout', required=True, type=int, default=480, help='Product timeout [minutes] - sync will be triggered if product will not reach station 55 within given time.')
    args = p.parse_args()
    
    return args


def main():
    args = parse_args()
    arg_map = vars(args)
    sys.argv = [sys.argv[0]]  # delete sysargv to satisfy traceability.helpers
    
    print arg_map
    
    from traceability.proda import DatabaseSync
    dbsync = DatabaseSync(arg_map)
    
    if arg_map['command'] == 'list-products':
        dbsync.list_sync_candidates(limit=arg_map['limit'])
    
    
        print "called", arg_map['command']


'''
def main():
    logger.info("Proda Sync Program Started")
    dbsync.list_sync_candidates(limit=10)
    product = dbsync.find_sync_data()
    dbsync.sync_single_product(product, dry_run=False)
    sync.prepare_products_for_proda_sync()
    sync.sync_all_products()
    logger.info("Proda Sync Program Finished")
'''

if __name__ == "__main__":
    main()
