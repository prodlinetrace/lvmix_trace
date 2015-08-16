from constants import PC_READY_FLAG, PLC_MESSAGE_FLAG, PLC_SAVE_FLAG, DB_BUSY_FLAG, PC_OPEN_BROWSER_FLAG, STATION_ID, PRODUCT_TYPE, SERIAL_NUMBER, WEEK_NUMBER, YEAR_NUMBER, DATE_TIME, PLC_HEARTBEAT_FLAG, PC_HEARTBEAT_FLAG, TRC_TMPL_COUNT, STATION_NUMBER, STATION_STATUS, PLC_TRC_ON
from plc.util import offset_spec_block

"""
Define DB blocks used.
"""

db3xxHead = """
0.0    {station_id}                 BYTE             # station_id of given PLC. (0-255 typically: 10, 11, 20, 21, 22, 23, 30, 31)
2.0    {product_type}               STRING[12]       # product_type from nameplate (10 digits)
16.0   {serial_number}              STRING[8]        # serial_number from nameplate (6 digits)
26.0   {week_number}                STRING[4]        # month number from nameplate (2 digits)
32.0   {year_number}                STRING[4]        # year number from nameplate  (2 digits)
38.0   {date_time}                  DATETIME         # size is 8 bytes
""".format(station_id=STATION_ID, product_type=PRODUCT_TYPE, serial_number=SERIAL_NUMBER, week_number=WEEK_NUMBER, year_number=YEAR_NUMBER, date_time=DATE_TIME)

db300Body = """
46.0   {flag_pc_ready}              BOOL        # PC_Ready bit. Monitored by PLC. PCL waits for True. PC sets to False when it starts processing. PC sets back to True once processing is finished.
46.1   {flag_plc_message}           BOOL        # PLC_Query bit - monitored by PC, set by PLC. PC reads status from database if set to True. Once PC finishes it sets it back to False.
46.2   {flag_plc_save}              BOOL        # PLC_Save bit - monitored by PC, set by PLC. PC saves status if set to True. Once PC finishes it sets it back to False.
46.3   {flag_db_busy}               BOOL        # DB_Busy bit - not really used currently.
46.4   {flag_pc_browser}            BOOL        # PC_OpenBrowser bit - monitored by PC, set by PLC. PC opens new browser tab with product details page if set to True (popups has to be enabled in program configuration). Once done it sets it back to False.
46.5   body.res_2                   BOOL
46.6   body.res_3                   BOOL
46.7   body.res_4                   BOOL
47.0   body.byte_res_1              BYTE
48.0   body.byte_res_2              BYTE
49.0   body.byte_res_3              BYTE
50.0   {station_number}             BYTE        # station_number - used when reading or saving station status. Value set by PLC when reading/writing status to/from database.
51.0   {station_status}             BYTE        # station_status - used when reading or saving station status. Value set by PLC when saving status. Value set by PC when reading status from database.
""".format(flag_pc_ready=PC_READY_FLAG, flag_plc_message=PLC_MESSAGE_FLAG, flag_plc_save=PLC_SAVE_FLAG, flag_db_busy=DB_BUSY_FLAG, flag_pc_browser=PC_OPEN_BROWSER_FLAG, station_number=STATION_NUMBER, station_status=STATION_STATUS)

db300Ctrl = """
52.0    {plc_live}                  BOOL        # blinks every 300[ms]. Indicates that PLC is alive.
52.1    {plc_trc_on}                BOOL        # traceability flag. used by PLC to indicate if tracaebility should be switched on.
52.2    ctrl.PLC_data_ready         BOOL        # not used.
52.3    ctrl.PLC_reserve            BOOL
52.4    {pc_live}                   BOOL        # Watched by PLC. PC should blink this bit every 300[ms] to notify that application is connected.
52.5    ctrl.PC_trc_on              BOOL        # not used
52.6    ctrl.PC_data_ready          BOOL        # not used
52.7    ctrl.PC_reserve             BOOL
53.0    ctrl.reserve                BYTE
""".format(plc_live=PLC_HEARTBEAT_FLAG, pc_live=PC_HEARTBEAT_FLAG, plc_trc_on=PLC_TRC_ON)

db300 = db3xxHead
db300 += db300Body
db300 += db300Ctrl


db3xxTrcHead = """
0.0    {trc_template_count}         BYTE        # number of traceability template blocks in message body.
1.0    body.res_1                   BYTE
""".format(trc_template_count=TRC_TMPL_COUNT)

db3xxTrcTail = """

"""

db3xxTrcTemplate = """
0.0    body.trc.tmpl.{number}.PC_Ready           BOOL        # PC_Ready bit - currently ignored
0.1    body.trc.tmpl.{number}.res_1              BOOL
0.2    body.trc.tmpl.{number}.PLC_Save           BOOL        # PLC_Save bit - monitored by PC. PC start block processing if set to True. Once PC finishes it sets it to False.
0.3    body.trc.tmpl.{number}.res_2              BOOL
0.4    body.trc.tmpl.{number}.res_3              BOOL
0.5    body.trc.tmpl.{number}.res_4              BOOL
0.6    body.trc.tmpl.{number}.res_5              BOOL
0.7    body.trc.tmpl.{number}.res_6              BOOL
1.0    body.trc.tmpl.{number}.res_byte           BYTE
2.0    body.trc.tmpl.{number}.operation_status   BYTE        # overall operation status. 1 - OK, 2 - NOK, 4 - Not present in this variant,  5 - next one OK, 6 - next one NOK
3.0    body.trc.tmpl.{number}.res_byte_0         BYTE
4.0    body.trc.tmpl.{number}.operation_type     INT         # individual operation type

6.0    body.trc.tmpl.{number}.1.result           REAL        # operation #1 - measured result.
10.0   body.trc.tmpl.{number}.1.result_max       REAL        # operation #1 - maximum value
14.0   body.trc.tmpl.{number}.1.result_min       REAL        # operation #1 - minimum value
18.0   body.trc.tmpl.{number}.1.result_status    INT         # operation #1 - status
20.0   body.trc.tmpl.{number}.1.word_res         INT         # not used - TODO: could be used as indication flag

22.0   body.trc.tmpl.{number}.2.result           REAL        # operation #2 - measured result.
26.0   body.trc.tmpl.{number}.2.result_max       REAL        # operation #2 - maximum value
30.0   body.trc.tmpl.{number}.2.result_min       REAL        # operation #2 - minimum value
34.0   body.trc.tmpl.{number}.2.result_status    INT         # operation #2 - status
36.0   body.trc.tmpl.{number}.2.word_res         INT

38.0   body.trc.tmpl.{number}.3.result           REAL        # operation #3 - measured result.
42.0   body.trc.tmpl.{number}.3.result_max       REAL        # operation #3 - maximum value
46.0   body.trc.tmpl.{number}.3.result_min       REAL        # operation #3 - minimum value
50.0   body.trc.tmpl.{number}.3.result_status    INT         # operation #3 - status
52.0   body.trc.tmpl.{number}.3.word_res         INT
54.0   body.trc.tmpl.{number}.date_time          DATETIME    # date and time - size is 8 bytes
# traceability template size is 62
"""

# create db map for given controller.
# controller id from config file should be used as key. currently controller id's are hardcoded
db_specs = {
      'c1': {},
      'c2': {},
      'c3': {},
      'c4': {},
      'c5': {},
      'c6': {},
}

def generate_db_spec(trcTemplateNumber=1):
    tmp_db = db3xxHead
    tmp_db += offset_spec_block(db3xxTrcHead, 46)
    for i in range(0, trcTemplateNumber):  # append traceability templates.
        base_offset = 48
        block_size = 62
        offset = base_offset + block_size * i
        tmp_db += offset_spec_block(db3xxTrcTemplate, offset).replace("{number}", str(i))

    return tmp_db


#############################################################################################
# St1x
#############################################################################################
db_specs['c1']['db300'] = db300
db_specs['c1']['db301'] = generate_db_spec(1)
db_specs['c1']['db302'] = generate_db_spec(2)
db_specs['c1']['db303'] = generate_db_spec(1)
db_specs['c1']['db304'] = generate_db_spec(10)

#############################################################################################
# St2x
#############################################################################################
db_specs['c2']['db300'] = db300
db_specs['c2']['db301'] = generate_db_spec(3)
db_specs['c2']['db302'] = generate_db_spec(1)
db_specs['c2']['db303'] = generate_db_spec(4)
db_specs['c2']['db304'] = generate_db_spec(5)

#############################################################################################
# St3x
#############################################################################################
db_specs['c3']['db300'] = db300
db_specs['c3']['db301'] = generate_db_spec(1)
db_specs['c3']['db302'] = generate_db_spec(3)
db_specs['c3']['db303'] = generate_db_spec(3)

#############################################################################################
# St4x
#############################################################################################
db_specs['c4']['db300'] = db300
db_specs['c4']['db301'] = generate_db_spec(4)
db_specs['c4']['db302'] = generate_db_spec(13)

#############################################################################################
# St5x
#############################################################################################
db_specs['c5']['db300'] = db300
db_specs['c5']['db301'] = generate_db_spec(1)
db_specs['c5']['db302'] = generate_db_spec(1)
db_specs['c5']['db303'] = generate_db_spec(1)
db_specs['c5']['db304'] = generate_db_spec(1)
db_specs['c5']['db305'] = generate_db_spec(2)

#############################################################################################
# St6x
#############################################################################################
db_specs['c6']['db300'] = db300
db_specs['c6']['db301'] = generate_db_spec(1)

# special cases hacking...
db310 = db300
db100 = ""
db101 = ""
db1 = ""
db2 = ""
db3 = ""
