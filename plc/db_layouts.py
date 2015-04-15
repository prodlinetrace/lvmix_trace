from constants import PC_READY_FLAG, PLC_MESSAGE_FLAG, PLC_SAVE_FLAG
from plc.util import offset_spec_block

"""
Define DB blocks used.
"""

db3xxHead = """
0.0    head.station_id              BYTE             # station_id of given PLC. (0-255 typically: 10, 11, 20, 21, 22, 23, 30, 31)
2.0    head.product_type            STRING[12]       # product_type from nameplate (10 digits)
16.0   head.serial_number           STRING[8]        # serial_number from nameplate (6 digits)
26.0   head.week_number             STRING[4]        # month number from nameplate (2 digits)
32.0   head.year_number             STRING[4]        # year number from nameplate  (2 digits)
38.0   head.date_time               DATETIME         # size is 8 bytes
"""

db300Body = """
46.0 """ + PC_READY_FLAG + """      BOOL        # PC_Ready flag. Monitored by PLC. PCL waits for True. PC sets to False when it starts processing. PC sets back to True once processing is finished.
46.1 """ + PLC_MESSAGE_FLAG + """   BOOL        # PLC_Query bit - monitored by PC. PC reads status from database if set to True. Once PC finishes it sets it back to False.
46.2 """ + PLC_SAVE_FLAG + """      BOOL        # PLC_Save bit - monitored by PC. PC saves status if set to True. Once PC finishes it sets it back to False.
46.4   body.res_1                   BOOL
46.5   body.res_2                   BOOL
46.6   body.res_3                   BOOL
46.7   body.res_4                   BOOL
47.0   body.byte_res_1              BYTE
48.0   body.byte_res_2              BYTE
49.0   body.byte_res_3              BYTE
50.0   body.station_number          BYTE        # station_number - used when reading or saving station status. Value set by PLC when reading/writing status to/from database.
51.0   body.station_status          BYTE        # station_status - used when reading or saving station status. Value set by PLC when saving status. Value set by PC when reading status from database.
"""

db300Ctrl = """
52.0    ctrl.plc.live                BOOL        # blinks every 300[ms]. Indicates that PLC is alive.
52.1    ctrl.plc.trc_on              BOOL        # traceability flag. used by PLC to indicate if tracaebility should be switched on.
52.2    ctrl.plc.data_ready          BOOL        # not used.
52.3    ctrl.plc.reserve             BOOL
52.4    ctrl.pc.live                 BOOL        # Watched by PLC. PC should blink this bit every 300[ms] to notify that application is connected.
52.5    ctrl.pc.trc_on               BOOL        # not used
52.6    ctrl.pc.data_ready           BOOL
52.7    ctrl.pc.reserve              BOOL
53.0    ctrl.reserve                 BYTE
"""

db300 = db3xxHead
db300 += db300Body
db300 += db300Ctrl


db3xxTrcHead = """
0.0    body.trc.template_count                 BYTE        # number of traceability template blocks in message body.
1.0    body.res_1                              BYTE
"""

db3xxTrcTail = """

"""

db3xxTrcTemplate = """
0.0    body.trc.tmpl.__no__.PC_Ready           BOOL        # PC_Ready bit - currently ignored
0.1    body.trc.tmpl.__no__.res_1              BOOL
0.2    body.trc.tmpl.__no__.PLC_Save           BOOL        # PLC_Save bit - monitored by PC. PC start block processing if set to True. Once PC finishes it sets it to False.
0.3    body.trc.tmpl.__no__.res_2              BOOL
0.4    body.trc.tmpl.__no__.res_3              BOOL
0.5    body.trc.tmpl.__no__.res_4              BOOL
0.6    body.trc.tmpl.__no__.res_5              BOOL
0.7    body.trc.tmpl.__no__.res_6              BOOL
1.0    body.trc.tmpl.__no__.res_byte           BYTE
2.0    body.trc.tmpl.__no__.operation_status   BYTE        # overall operation status. 1 - OK, 2 - NOK, 4 - Not present in this variant,  5 - next one OK, 6 - next one NOK
3.0    body.trc.tmpl.__no__.res_byte_0         BYTE
4.0    body.trc.tmpl.__no__.operation_type     INT         # individual operation type

6.0    body.trc.tmpl.__no__.1.result           REAL        # operation #1 - measured result.
10.0   body.trc.tmpl.__no__.1.result_max       REAL        # operation #1 - maximum value
14.0   body.trc.tmpl.__no__.1.result_min       REAL        # operation #1 - minimum value
18.0   body.trc.tmpl.__no__.1.result_status    INT         # operation #1 - status
20.0   body.trc.tmpl.__no__.1.word_res         WORD        # not used - TODO: could be used as indication flag

22.0   body.trc.tmpl.__no__.2.result           REAL        # operation #2 - measured result.
26.0   body.trc.tmpl.__no__.2.result_max       REAL        # operation #2 - maximum value
30.0   body.trc.tmpl.__no__.2.result_min       REAL        # operation #2 - minimum value
34.0   body.trc.tmpl.__no__.2.result_status    INT         # operation #2 - status
36.0   body.trc.tmpl.__no__.2.word_res         WORD

38.0   body.trc.tmpl.__no__.3.result           REAL        # operation #3 - measured result.
42.0   body.trc.tmpl.__no__.3.result_max       REAL        # operation #3 - maximum value
46.0   body.trc.tmpl.__no__.3.result_min       REAL        # operation #3 - minimum value
50.0   body.trc.tmpl.__no__.3.result_status    INT         # operation #3 - status
52.0   body.trc.tmpl.__no__.3.word_res         WORD
54.0   body.trc.tmpl.__no__.date_time          DATETIME    # date and time - size is 8 bytes
# traceability template size is 62
"""


db301 = db3xxHead
db301 += offset_spec_block(db3xxTrcHead, 46)
for i in range(0, 3):  # append 3 traceability templates.
    base_offset = 48
    block_size = 62
    offset = base_offset + block_size * i
    db301 += offset_spec_block(db3xxTrcTemplate, offset).replace("__no__", str(i))


db302 = db3xxHead
db302 += offset_spec_block(db3xxTrcHead, 46)
for i in range(0, 1):  # append 1 traceability template.
    base_offset = 48
    block_size = 62
    offset = base_offset + block_size * i
    db302 += offset_spec_block(db3xxTrcTemplate, offset).replace("__no__", str(i))

db303 = db3xxHead
db303 += offset_spec_block(db3xxTrcHead, 46)
for i in range(0, 4):  # append 4 traceability templates.
    base_offset = 48
    block_size = 62
    offset = base_offset + block_size * i
    db303 += offset_spec_block(db3xxTrcTemplate, offset).replace("__no__", str(i))

db304 = db3xxHead
db304 += offset_spec_block(db3xxTrcHead, 46)
for i in range(0, 5):  # append 5 traceability templates.
    base_offset = 48
    block_size = 62
    offset = base_offset + block_size * i
    db304 += offset_spec_block(db3xxTrcTemplate, offset).replace("__no__", str(i))


# special cases hacking...
db310 = db300
db100 = ""
db101 = ""
db1 = ""
db2 = ""
db3 = ""