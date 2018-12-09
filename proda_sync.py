#!/usr/bin/env python2
import logging
import sys
import os
import textwrap
import dateparser 
import argparse 
import ConfigParser

logger = logging.getLogger(__name__)


def get_help(prog_name='executable'):
    h = """
        To list available products please execute:
        {prog_name} list-products

        To sync one selected product please execute:
        {prog_name} sync-one

        To sync all products please execute:
        {prog_name} sync-all --start-date --end-date --wabco-number --limit

        To remove old records (statuses, operations and optionally products) please execute:
        {prog_name} remove-old-records --start-date --end-date --wabco-number --serial --limit

        To enforce sync of possibly missing statuses or operations please execute 
        {prog_name} sync-missing-records --start-date --end-date --wabco-number --serial --limit

    """.format(prog_name=prog_name)

    return textwrap.dedent(h)

def valid_date(s):
    date = dateparser.parse(s)
    if date is None:
        raise argparse.ArgumentTypeError("Not a valid date: '{0}'.".format(s))
    return date

def parse_args():
    # set some defaults
    prog_name = os.path.basename(sys.argv[0])
    file_name, file_extension = os.path.splitext(prog_name)
    conf_file = os.path.join(".".join([file_name, "conf"]))
    logfile = os.path.join(".".join([file_name, "log"]))
    log_level = logging.INFO
    proda_uri = "prodang/wabco@PTT"
    dburi = "mysql+pymysql://trace:trace@localhost:3307/trace2"
    
    early_parser = argparse.ArgumentParser(add_help=False)
    early_parser.add_argument('-c', '--config', required=False, default=conf_file, help='config file path')
    early_args, remainder_argv = early_parser.parse_known_args()
    
    if not os.path.exists(early_args.config): 
        early_parser.error("Selected config file: %s does not exist!" % early_args.config)
    
    # get some defines from config file
    cp = ConfigParser.RawConfigParser(allow_no_value=True)
    cp.read(early_args.config)
    if 'main' in cp.sections():
        for k, v in list(cp.items('main')):
            exec("""{0} = '{1}'""".format(k, v))
    
    parser = argparse.ArgumentParser(
        description="Tool to manage tracedb - proda sync operations.\n\n",
        epilog=get_help(prog_name),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--logfile', required=False, type=str, default=logfile, help='logfile path')
    parser.add_argument('--loglevel', action="store", required=False, type=int, default=log_level, help='URI for tracedb connectivity')
    parser.add_argument('-v', help='verbose mode', action='store_true')
    parser.add_argument('-q', help='quiet mode', action='store_true')
    parser.add_argument('--dburi', required=False, type=str, default=dburi, help='URI for tracedb connectivity')
    parser.add_argument('--proda_uri', required=False, type=str, default=proda_uri, help='URI for PRODA connectivity')
    
    subparsers = parser.add_subparsers(dest="command", title="commands")
    parser_list_products = subparsers.add_parser('list-products', help="List most recent products from tracedb")
    parser_list_products.add_argument('--limit', required=False, type=int, default=10, help='Limit number of returned records. Use 0 to look for all.')
    parser_list_products.add_argument('--prodasync', required=False, type=int, default=-1, help='prodasync value. Use -1 or leave undefined to look for all.')
    parser_list_products.add_argument('--start-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS. Also dateparser formats are accepted, eg. "2 weeks ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_list_products.add_argument('--end-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS Also dateparser formats are accepted, eg. "3 months, 1 week and 1 day ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_list_products.add_argument('-i', '--wabco-number-include', type=int, default=[], action="append", help='wabco-number / type to search for. Leave empty to look for all.')
    parser_list_products.add_argument('-e', '--wabco-number-exclude', type=int, default=[], action='append', help='Filter out given wabco-number. Can be used more than once.')
    
    parser_sync_one = subparsers.add_parser('sync-one', help="Sync one selected product from tracedb to proda")
    parser_sync_one.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status non zero (already synced).')
    parser_sync_one.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    parser_sync_one.add_argument('wabco-number', type=int, default=4640061000, help='wabco-number to sync')
    parser_sync_one.add_argument('serial', type=int, default=123456, help='serial to sync')
    
    #{prog_name} sync-all --start-time --end-time --wabco-number --limit
    parser_sync_all = subparsers.add_parser('sync-all')
    parser_sync_all.add_argument('--product_timeout', required=False, type=int, default=480, help='Product timeout [minutes] - sync will be triggered if product will not reach station 55 within given time.')
    parser_sync_all.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status is non zero (already synced).')
    parser_sync_all.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    parser_sync_all.add_argument('--start-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS. Also dateparser formats are accepted, eg. "2 weeks ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_sync_all.add_argument('--end-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS Also dateparser formats are accepted, eg. "3 months, 1 week and 1 day ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_sync_all.add_argument('--limit', type=int, default=0, help='Limit number of records. Use 0 - for all (default).')
    parser_sync_all.add_argument('-i', '--wabco-number-include', type=int, default=[], action='append', help='limit to specific wabco-number. Leave empty for all (default). Can be used more than once.')
    parser_sync_all.add_argument('-e', '--wabco-number-exclude', type=int, default=[], action='append', help='Filter out given wabco-number. Can be used more than once.')

    #{prog_name} remove-old-records --start-date --end-date --wabco-number --serial --limit
    parser_remove_old_records = subparsers.add_parser('remove-old-records')
    parser_remove_old_records.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status non zero (already synced).')
    parser_remove_old_records.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    parser_remove_old_records.add_argument('--start-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS. Also dateparser formats are accepted, eg. "2 weeks ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_remove_old_records.add_argument('--end-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS Also dateparser formats are accepted, eg. "3 months, 1 week and 1 day ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_remove_old_records.add_argument('--limit', type=int, default=0, help='Limit number of records. Use 0 - for all (default).')
    parser_remove_old_records.add_argument('-i', '--wabco-number-include', type=int, default=[], action='append', help='limit to specific wabco-number. Leave empty for all (default). Can be used more than once.')
    parser_remove_old_records.add_argument('-e', '--wabco-number-exclude', type=int, default=[], action='append', help='Filter out given wabco-number. Can be used more than once.')
    parser_remove_old_records.add_argument('-s', '--serial', type=int, default=0, help='limit to specific serial (use six digit format). Use 0 - for all (default).')

    #{prog_name} sync-missing --start-date --end-date --wabco-number --serial --limit
    parser_sync_missing_records = subparsers.add_parser('sync-missing-records')
    parser_sync_missing_records.add_argument('--force', action='store_true', default=False, help='Enforce sync even if product status non zero (already synced).')
    parser_sync_missing_records.add_argument('--dry-run', action='store_true', default=False, help='do not really commit any changes to databases.')
    parser_sync_missing_records.add_argument('--start-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS. Also dateparser formats are accepted, eg. "2 weeks ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_sync_missing_records.add_argument('--end-date', default=None, help='Please specify start time for sync. Format: YYYY-MM-DD HH:MM:SS Also dateparser formats are accepted, eg. "3 months, 1 week and 1 day ago". See: https://dateparser.readthedocs.io/en/latest/', type=valid_date)
    parser_sync_missing_records.add_argument('--limit', type=int, default=0, help='Limit number of records. Use 0 - for all (default).')
    parser_sync_missing_records.add_argument('-i', '--wabco-number-include', type=int, default=[], action='append', help='limit to specific wabco-number. Leave empty for all (default). Can be used more than once.')
    parser_sync_missing_records.add_argument('-e', '--wabco-number-exclude', type=int, default=[], action='append', help='Filter out given wabco-number. Can be used more than once.')
    parser_sync_missing_records.add_argument('-s', '--serial', type=int, default=0, help='limit to specific serial (use six digit format). Use 0 - for all (default).')
    
    args = parser.parse_args(remainder_argv)
    
    return args


def main():
    logger.info("Proda Sync Program Started")
    args = parse_args()
    arg_map = vars(args)
    sys.argv = [sys.argv[0]]  # delete sys.argv to satisfy traceability.helpers
    # print arg_map
    from traceability.proda import DatabaseSync
    dbsync = DatabaseSync(arg_map)
    
    def list_products():
        dbsync.list_sync_candidates(wabco_number_include=arg_map['wabco_number_include'], wabco_number_exclude=arg_map['wabco_number_exclude'], limit=arg_map['limit'], proda_sync=arg_map['prodasync'], start_date=arg_map['start_date'], end_date=arg_map['end_date'])
    
    def sync_one():
        product = dbsync.get_one_product(wabco_number=arg_map['wabco_number'], serial=arg_map['serial'])
        dbsync.set_sync_ready_flag(product, dry_run=arg_map['dry_run'], force=arg_map['force'])  # reset prodasync flag to enable processing
        dbsync.sync_single_product(product, dry_run=arg_map['dry_run'], force=arg_map['force'])
    
    def sync_all():
        dbsync.prepare_products_for_proda_sync(dry_run=arg_map['dry_run'], force=arg_map['force'], start_date=arg_map['start_date'], end_date=arg_map['end_date'], limit=arg_map['limit'], wabco_number_include=arg_map['wabco_number_include'], wabco_number_exclude=arg_map['wabco_number_exclude'], product_timeout=arg_map['product_timeout'])
        dbsync.sync_all_products(dry_run=arg_map['dry_run'], force=arg_map['force'], wabco_number_include=arg_map['wabco_number_include'], wabco_number_exclude=arg_map['wabco_number_exclude'])
    
    def remove_old_records():
        dbsync.remove_old_records(dry_run=arg_map['dry_run'], force=arg_map['force'], start_date=arg_map['start_date'], end_date=arg_map['end_date'], limit=arg_map['limit'], wabco_number_include=arg_map['wabco_number_include'], wabco_number_exclude=arg_map['wabco_number_exclude'], serial=arg_map['serial'])

    def sync_missing_records():
        dbsync.sync_missing_records(dry_run=arg_map['dry_run'], force=arg_map['force'], start_date=arg_map['start_date'], end_date=arg_map['end_date'], limit=arg_map['limit'], wabco_number_include=arg_map['wabco_number_include'], wabco_number_exclude=arg_map['wabco_number_exclude'], serial=arg_map['serial'])
    
    commands = {
        'list-products': list_products,
        'sync-one': sync_one, 
        'sync-all': sync_all, 
        'remove-old-records': remove_old_records, 
        'sync-missing-records': sync_missing_records,
    }

    def run(argument):
        func = commands.get(argument, "nothing")
        # Execute the function
        return func()
 
    # print("Running command: {0}".format(arg_map['command']))
    run(arg_map['command'])  # run given command.
    
    logger.info("Proda Sync Program Finished")


if __name__ == "__main__":
    main()
