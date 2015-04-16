PC_READY_FLAG       = 'body.PC_Ready'
PLC_MESSAGE_FLAG    = 'body.PLC_Query'
PLC_SAVE_FLAG       = 'body.PLC_Save'

STATION_NUMBER      = 'body.station_number'  # byte
STATION_STATUS      = 'body.station_status'  # byte
STATION_ID          = 'head.station_id'      # byte
SERIAL_NUMBER       = 'head.serial_number'   # string(8)
PRODUCT_TYPE        = 'head.product_type'   # string(12)

PC_HEARTBEAT_FLAG   = 'ctrl.pc.live'
PLC_HEARTBEAT_FLAG  = 'ctrl.plc.live'

TRC_TMPL_COUNT      = 'body.trc.template_count'
TRC_TMPL_SAVE_FLAG  = 'body.trc.tmpl.__no__.PLC_Save'

SQLALCHEMY_DATABASE_URI_PREFIX = 'sqlite:///'

STATION_STATUS_CODES = {
    0: {"result": "UNDEFINED", "desc": "status undefined (not present in database)"},
    1: {"result": "OK", "desc": "Status ok"},
    2: {"result": "NOK", "desc": "Status not ok"},
    4: {"result": "NOTAVAILABLE", "desc": "Not present in given type"},
    5: {"result": "REPEATEDOK", "desc": "Repeated test was ok"},
    6: {"result": "REPEATEDNOK", "desc": "Repeated test was not ok"},
    9: {"result": "WAITING", "desc": "status reset - PLC set status to 'WAITING' and waiting for PC response"},
    10: {"result": "INTERRUPTED", "desc": "Test was interrupted"},
    11: {"result": "REPEATEDINTERRUPTED", "desc": "Repeated test was interrupted"},
    99: {"result": "VALUEERROR", "desc": "Faulty value was passed. Unable to process data."},
}
