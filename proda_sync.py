#!/usr/bin/env python2
import logging
import sys
import os
import configargparse
import textwrap
from argparse import RawTextHelpFormatter, ArgumentParser

logger = logging.getLogger(__name__)


def get_help(prog_name='executable'):
    h = """
        To list available products please execute:
        {prog_name} list-products

        To sync one selected product please execute:
        {prog_name} sync-one

        To sync all products please execute:
        {prog_name} sync-all

        {prog_name} set-ready-to-sync
                
        To remove old records please execute:
        {prog_name} remove-old-records

    """.format(prog_name=prog_name)

    return textwrap.dedent(h)


def parse_args():
    prog_name = os.path.basename(sys.argv[0])
    file_name, file_extension = os.path.splitext(prog_name)
    conf_file = os.path.join(".".join([file_name, "conf"]))
    log_file = os.path.join(".".join([file_name, "log"]))
    """
    p = configargparse.ArgParser(
        default_config_files=['~/.my_conf', conf_file],
        description="Tool to manage tracedb - proda sync operations.\n\n",
        epilog=get_help(prog_name),
        formatter_class=RawTextHelpFormatter,
    )
    """
    p = ArgumentParser(
        description="Tool to manage tracedb - proda sync operations.\n\n",
        epilog=get_help(prog_name),
        formatter_class=RawTextHelpFormatter,
    )
    #p.add_argument('command', help='command to execute', choices=['list-products', 'sync-one-product', 'sync-all', 'remove-old-records'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('--logfile', required=False, type=str, default=log_file, help='logfile path')
    p.add_argument('--loglevel', action="store", required=False, type=int, default=logging.INFO, help='URI for tracedb connectivity')
    p.add_argument('-v', help='verbose mode', action='store_true')
    p.add_argument('-q', help='quiet mode', action='store_true')
    p.add_argument('--dburi', required=False, type=str, help='URI for tracedb connectivity')
    p.add_argument('--proda_uri', required=False, type=str, default="prodang/wabco@PT", help='URI for PRODA connectivity')
    
    subparsers = p.add_subparsers(dest="command", title="commands")
    parser_list_products = subparsers.add_parser('list-products', help="List most recent products from tracedb")
    parser_list_products.add_argument('--limit', required=False, type=int, default=10, help='Limit number of returned records.')
    parser_list_products.add_argument('--prodasync', required=False, type=int, default=-1, help='prodasync value. Use -1 or leave undefined to look for all.')
    parser_list_products.add_argument('wabco_number', type=int, default=4640061000, help='wabco_number / type to look for')
    
    parser_sync_one = subparsers.add_parser('sync-one', help="Sync one selected product from tracedb to proda")
    parser_sync_one.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status is - 2 (already synced).')
    parser_sync_one.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    parser_sync_one.add_argument('wabco_number', type=int, default=4640061000, help='wabco_number to sync')
    parser_sync_one.add_argument('serial', type=int, default=123456, help='serial to sync')
    
    parser_sync_all = subparsers.add_parser('sync-all')
    parser_sync_all.add_argument('--product_timeout', required=False, type=int, default=480, help='Product timeout [minutes] - sync will be triggered if product will not reach station 55 within given time.')
    parser_sync_all.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status is - 2 (already synced).')
    parser_sync_all.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')

    parser_remove_old_records = subparsers.add_parser('remove-old-records')
    parser_remove_old_records.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status is - 2 (already synced).')
    parser_remove_old_records.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    
    args = p.parse_args()
    
    return args


def main():
    logger.info("Proda Sync Program Started")
    args = parse_args()
    arg_map = vars(args)
    sys.argv = [sys.argv[0]]  # delete sys.argv to satisfy traceability.helpers
    #print arg_map
    
    from traceability.proda import DatabaseSync
    dbsync = DatabaseSync(arg_map)
    
    def list_products():
        dbsync.list_sync_candidates(wabco_number=arg_map['wabco_number'], limit=arg_map['limit'], proda_sync=arg_map['prodasync'])
    
    def sync_one():
        product = dbsync.get_one_product(wabco_number=arg_map['wabco_number'], serial=arg_map['serial'])
        dbsync.sync_single_product(product, dry_run=arg_map['dry_run'], force=arg_map['force'])
    
    def sync_all():
        #sync.prepare_products_for_proda_sync()
        #sync.sync_all_products()
        # TODO: implement me
        pass
    
    def remove_old_records():
        # TODO: implement me
        pass
    
    commands = {
        'list-products': list_products,
        'sync-one': sync_one, 
        'sync-all': sync_all, 
        'remove-old-records': remove_old_records, 
    }

    def run(argument):
        func = commands.get(argument, "nothing")
        # Execute the function
        return func()
 
    #print("Running command: {0}".format(arg_map['command']))
    run(arg_map['command'])
    
    logger.info("Proda Sync Program Finished")


if __name__ == "__main__":
    main()
