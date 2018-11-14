#!/usr/bin/env python
#-*- coding: utf-8 -*-
import logging
import sys
import os
#import configargparse
import textwrap
from argparse import RawTextHelpFormatter, ArgumentParser
from traceability.proda import DatabaseSync
import argparse

logger = logging.getLogger(__name__)


def help(prog_name='executable'):
    h = """
        To list all available CMQA releases with corresponding FIXGW version please run (limit set to 50 by default):
        {prog_name}

        To list last 100 CMQA releases with corresponding FIXGW version please run:
        {prog_name} -l 100

        To find FIXGW version for specific T7 release e.g. 005.000.161 please run:
        {prog_name} -r 005.000.161
    """.format(prog_name=prog_name)

    return textwrap.dedent(h)


def parse_args():
    prog_name = os.path.basename(sys.argv[0])
    file_name, file_extension = os.path.splitext(prog_name)
    conf_file = os.path.join(".".join([file_name, "conf"]))
    log_file = os.path.join(".".join([file_name, "log"]))
    #p = configargparse.ArgParser(
    #p = configargparse.get_argument_parser(
    p = argparse.ArgumentParser(
        #default_config_files=['~/.my_conf', conf_file],
        description="Tool to manage tracedb - proda sync operations.\n\n",
        epilog=help(prog_name),
        formatter_class=RawTextHelpFormatter,
    )
    p.add_argument("-x", help="Main module setting")
    p.add_argument("-e", help="add arg")
    #p.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('--logfile', required=False, type=str, default=log_file, help='logfile path')
    p.add_argument('-l', '--log', dest='loglevel', action="store", required=False, type=int, default=logging.INFO, help='URI for tracedb connectivity')
    p.add_argument('-v', help='verbose mode', action='store_true')
    #p.add_argument('-q', help='quiet mode', action='store_true')
    p.add_argument('--limit', required=False, type=int, default=10, help='Limit number of returned records.')
    #p.add_argument('--dburi', required=True, type=str, help='URI for tracedb connectivity')
    #p.add_argument('--proda_uri', required=True, type=str, help='URI for PRODA connectivity')
    #p.add_argument('--product_timeout', required=True, type=int, default=480, help='Product timeout [minutes] - sync will be triggered if product will not reach station 55 within given time.')
    args = p.parse_args()
    #args = p.parse_known_args()

    print(p.format_help())
    #print(p.format_values()) 
    
    return args


def main():
    args = parse_args()
    #print args
    print vars(args)
    dbsync = DatabaseSync(vars(args))
    dbsync.list_sync_candidates(limit=10)

    #if args.release:
    #    print f4t.get_fixgw_version(args.release)
    #else:
    #    f4t.print_t7_fixgw_map(args.limit)


'''
def main():
    logger.info("Proda Sync Program Started")
    p = configargparse.ArgParser(default_config_files=['~/.my_settings', os.path.basename(sys.argv[0]).rstrip('py')+'confa'])
    p.add('-c', '--config', is_config_file=True)
    options = p.parse_args() #args, namespace, config_file_contents, env_vars
    print options
    dbsync = DatabaseSync(sys.argv)
    
    dbsync.list_sync_candidates(limit=10)
    #product = dbsync.find_sync_data()
    #dbsync.sync_single_product(product, dry_run=False)
    #sync.prepare_products_for_proda_sync()
    #sync.sync_all_products()
    logger.info("Proda Sync Program Finished")
'''

if __name__ == "__main__":
    main()
